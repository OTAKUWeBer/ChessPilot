import 'dart:convert';
import 'package:flutter/services.dart';

class AndroidPlatform {
  static const channel = MethodChannel('chesspilot/android');
  Future<Map<String, dynamic>> connect() async =>
      jsonDecode((await channel.invokeMethod<String>('connect'))!)
          as Map<String, dynamic>;
  Future<Map<String, dynamic>> status() async => Map<String, dynamic>.from(
    (await channel.invokeMapMethod<String, dynamic>('status'))!,
  );
  Future<void> action(String name) => channel.invokeMethod<void>(name);
}
