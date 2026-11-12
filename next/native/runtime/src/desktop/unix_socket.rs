use std::{
    io,
    mem::{size_of, zeroed},
    os::{
        fd::{AsRawFd, FromRawFd, OwnedFd},
        unix::{ffi::OsStrExt, net::UnixStream},
    },
    path::Path,
    thread,
    time::{Duration, Instant},
};
pub fn poll(fd: i32, events: i16, deadline: Instant) -> io::Result<()> {
    loop {
        let remaining = deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() {
            return Err(io::ErrorKind::TimedOut.into());
        }
        let mut descriptor = libc::pollfd {
            fd,
            events,
            revents: 0,
        };
        let result = unsafe {
            libc::poll(
                &mut descriptor,
                1,
                remaining.as_millis().clamp(1, i32::MAX as u128) as i32,
            )
        };
        if result > 0 {
            if descriptor.revents & libc::POLLNVAL != 0 {
                return Err(io::ErrorKind::BrokenPipe.into());
            }
            return Ok(());
        }
        if result == 0 {
            return Err(io::ErrorKind::TimedOut.into());
        }
        let error = io::Error::last_os_error();
        if error.kind() != io::ErrorKind::Interrupted {
            return Err(error);
        }
    }
}
pub fn connect(path: &Path, abstract_name: bool, timeout: Duration) -> io::Result<UnixStream> {
    let bytes = path.as_os_str().as_bytes();
    let mut address: libc::sockaddr_un = unsafe { zeroed() };
    if bytes.is_empty() || bytes.contains(&0) || bytes.len() + 1 > address.sun_path.len() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "Invalid Unix socket path",
        ));
    }
    address.sun_family = libc::AF_UNIX as _;
    let start = usize::from(abstract_name);
    for (i, &byte) in bytes.iter().enumerate() {
        address.sun_path[start + i] = byte as _;
    }
    let raw = unsafe {
        libc::socket(
            libc::AF_UNIX,
            libc::SOCK_STREAM | libc::SOCK_CLOEXEC | libc::SOCK_NONBLOCK,
            0,
        )
    };
    if raw < 0 {
        return Err(io::Error::last_os_error());
    }
    let fd = unsafe { OwnedFd::from_raw_fd(raw) };
    let length = std::mem::offset_of!(libc::sockaddr_un, sun_path) + bytes.len() + 1;
    let deadline = Instant::now() + timeout;
    loop {
        let result = unsafe {
            libc::connect(
                fd.as_raw_fd(),
                (&address as *const libc::sockaddr_un).cast(),
                length as _,
            )
        };
        if result == 0 {
            break;
        }
        let error = io::Error::last_os_error();
        match error.raw_os_error() {
            Some(libc::EINPROGRESS) => {
                poll(fd.as_raw_fd(), libc::POLLOUT, deadline)?;
                let mut code: i32 = 0;
                let mut size = size_of::<i32>() as libc::socklen_t;
                if unsafe {
                    libc::getsockopt(
                        fd.as_raw_fd(),
                        libc::SOL_SOCKET,
                        libc::SO_ERROR,
                        (&mut code as *mut i32).cast(),
                        &mut size,
                    )
                } < 0
                {
                    return Err(io::Error::last_os_error());
                }
                if code != 0 {
                    return Err(io::Error::from_raw_os_error(code));
                }
                break;
            }
            Some(libc::EAGAIN) => {
                if Instant::now() >= deadline {
                    return Err(io::ErrorKind::TimedOut.into());
                }
                thread::sleep(Duration::from_millis(5));
            }
            _ => return Err(error),
        }
    }
    let stream = UnixStream::from(fd);
    stream.set_nonblocking(false)?;
    Ok(stream)
}
