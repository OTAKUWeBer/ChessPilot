package io.github.otakuweber.chesspilot

import java.io.File
import java.io.InputStream
import java.security.MessageDigest

// Android's rename replaces atomically; Windows JVM tests supply their equivalent.
internal fun installPackagedAsset(
    target: File,
    expected: String,
    replace: (File, File) -> Unit = { source, destination ->
        check(source.renameTo(destination)) { "Cannot install packaged asset: ${destination.name}" }
    },
    openAsset: () -> InputStream,
) {
    check(expected.matches(Regex("[0-9a-f]{64}"))) { "Invalid packaged asset checksum: ${target.name}" }
    fun digest(file: File): String {
        val hash = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(65536)
            while (true) {
                val size = input.read(buffer)
                if (size < 0) break
                hash.update(buffer, 0, size)
            }
        }
        return hash.digest().joinToString("") { "%02x".format(it.toInt() and 255) }
    }
    if (target.isFile && digest(target) == expected) return
    val temporary = File(target.parentFile, "${target.name}.part")
    try {
        openAsset().use { input ->
            temporary.outputStream().use { output -> input.copyTo(output); output.fd.sync() }
        }
        check(digest(temporary) == expected) { "Invalid packaged asset: ${target.name}" }
        replace(temporary, target)
    } finally {
        temporary.delete()
    }
}
