import 'dart:io';

/// Flutter's pubspec is the release authority; Cargo mirrors its semantic version.
String semanticVersion(String release) {
  final match = RegExp(
    r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?\+([1-9]\d*)$',
  ).firstMatch(release);
  if (match == null ||
      match.group(0) != release ||
      [
        1,
        2,
        3,
        5,
      ].any((i) => (int.tryParse(match.group(i)!) ?? 65536) > 65535) ||
      (match
              .group(4)
              ?.split('.')
              .any(
                (part) =>
                    RegExp(r'^\d+$').hasMatch(part) &&
                    part.length > 1 &&
                    part.startsWith('0'),
              ) ??
          false)) {
    throw FormatException(
      'Use MAJOR.MINOR.PATCH[-prerelease]+BUILD; numeric version/build fields must fit 0–65535, with BUILD at least 1.',
    );
  }
  return release.split('+').first;
}

String replaceVersion(
  String text,
  RegExp pattern,
  String replacement,
  int count,
) {
  if (pattern.allMatches(text).length != count) {
    throw FormatException(
      'Unexpected version layout; refusing to modify this file.',
    );
  }
  return text.replaceAllMapped(pattern, (m) => '${m[1]}$replacement${m[2]}');
}

Map<String, String> versionPlan(Directory root, String release) {
  final semantic = semanticVersion(release);
  String read(String name) => File('${root.path}/$name').readAsStringSync();
  return {
    'app/pubspec.yaml': replaceVersion(
      read('app/pubspec.yaml'),
      RegExp(r'^(version:\s*)[^\r\n]+(\r?)$', multiLine: true),
      release,
      1,
    ),
    'native/Cargo.toml': replaceVersion(
      read('native/Cargo.toml'),
      RegExp(r'(\[workspace\.package\]\s*version = ")[^"]+(")'),
      semantic,
      1,
    ),
    'native/Cargo.lock': replaceVersion(
      read('native/Cargo.lock'),
      RegExp(
        r'(\[\[package\]\]\r?\nname = "chesspilot-(?:core|runtime)"\r?\nversion = ")[^"]+(")',
      ),
      semantic,
      2,
    ),
  };
}

void main(List<String> args) {
  try {
    final root = File.fromUri(Platform.script).parent.parent;
    final check = args.length == 1 && args.single == '--check';
    if (args.length != 1)
      throw const FormatException(
        'Usage: dart tool/version.dart VERSION+BUILD | --check',
      );
    final current = RegExp(r'^version:\s*([^\r\n]+)', multiLine: true)
        .firstMatch(File('${root.path}/app/pubspec.yaml').readAsStringSync())
        ?.group(1);
    final release = check ? current ?? '' : args.single;
    final plan = versionPlan(root, release);
    final changed = plan.keys
        .where(
          (name) => File('${root.path}/$name').readAsStringSync() != plan[name],
        )
        .toList();
    if (check && changed.isNotEmpty) {
      throw FormatException(
        'Version mismatch in ${changed.join(', ')}. Run dart tool/version.dart $release',
      );
    }
    if (!check) {
      for (final name in changed) {
        File('${root.path}/$name').writeAsStringSync(plan[name]!);
      }
    }
    stdout.writeln(
      'Release $release: ${check ? 'versions agree' : '${changed.length} file(s) updated'}.',
    );
  } on Object catch (error) {
    stderr.writeln(error);
    exitCode = 1;
  }
}
