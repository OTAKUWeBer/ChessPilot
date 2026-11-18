import 'dart:io';
import '../version.dart';

void main() {
  assert(semanticVersion('1.2.3+4') == '1.2.3');
  assert(semanticVersion('3.0.0-rc.2+9') == '3.0.0-rc.2');
  for (final invalid in [
    '1.2+3',
    '01.2.3+4',
    '1.2.3+0',
    '1.2.3+65536',
    '1.2.3-rc.01+1',
    '1.2.3+1\nquit',
    '1.2.3+1\n',
  ]) {
    var rejected = false;
    try {
      semanticVersion(invalid);
    } on FormatException {
      rejected = true;
    }
    assert(rejected, invalid);
  }
  final root = Directory.systemTemp.createTempSync('chesspilot-version-');
  var cleanupRefused = false;
  try {
    File('${root.path}/app/pubspec.yaml')
      ..parent.createSync()
      ..writeAsStringSync('name: chesspilot\nversion: 1.2.3+4\n');
    File('${root.path}/native/Cargo.toml')
      ..parent.createSync()
      ..writeAsStringSync(
        '[workspace]\nmembers = ["core", "runtime"]\n[workspace.package]\nversion = "1.2.3"\n',
      );
    File('${root.path}/native/Cargo.lock').writeAsStringSync(
      '[[package]]\nname = "chesspilot-core"\nversion = "1.2.3"\n\n[[package]]\nname = "chesspilot-runtime"\nversion = "1.2.3"\n\n[[package]]\nname = "dependency"\nversion = "9.9.9"\n',
    );
    final plan = versionPlan(root, '2.0.0-rc.1+5');
    assert(plan['app/pubspec.yaml']!.contains('version: 2.0.0-rc.1+5'));
    assert(plan['native/Cargo.toml']!.contains('version = "2.0.0-rc.1"'));
    assert(
      'version = "2.0.0-rc.1"'.allMatches(plan['native/Cargo.lock']!).length ==
          2,
    );
    assert(plan['native/Cargo.lock']!.contains('version = "9.9.9"'));
    assert(
      File(
        '${root.path}/app/pubspec.yaml',
      ).readAsStringSync().contains('1.2.3+4'),
    );
    File('${root.path}/native/Cargo.toml').writeAsStringSync('[workspace]\n');
    var rejected = false;
    try {
      versionPlan(root, '2.0.0+5');
    } on FormatException {
      rejected = true;
    }
    assert(rejected);
  } finally {
    // Only the unique directory created by this test is removed.
    if (!root.resolveSymbolicLinksSync().startsWith(
      '${Directory.systemTemp.resolveSymbolicLinksSync()}${Platform.pathSeparator}',
    )) {
      cleanupRefused = true;
    } else {
      root.deleteSync(recursive: true);
    }
  }
  if (cleanupRefused) {
    throw StateError('Temporary test directory escaped the system temp folder');
  }
  stdout.writeln('Version validation and update-plan checks passed.');
}
