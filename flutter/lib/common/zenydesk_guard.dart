import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher_string.dart';

import '../common.dart';
import '../common/widgets/login.dart';
import '../models/platform_model.dart';

/// ZenyDesk Commercial Guard & Direct Session Gatekeeper
/// Enforces business rules, authentication, and daily quotas safely across all platforms.
class ZenydeskGuard {
  static Timer? _heartbeatTimer;
  static String? _activeSessionId;
  static String? _cachedApiUrl;
  static String? _cachedToken;

  /// Universal Pre-Connect Gatekeeper
  /// Checks technician authentication, plan features, and daily quotas before establishing connection.
  /// Returns true to proceed, false to abort.
  static Future<bool> preConnectCheck(
    BuildContext context,
    String peerId, {
    bool isTerminal = false,
    bool isFileTransfer = false,
  }) async {
    // 1. GATE 1: Technician Authentication Check
    if (!gFFI.userModel.isLogin) {
      final shouldLogin = await _showLoginRequiredDialog();
      if (shouldLogin == true) {
        final loggedIn = await loginDialog();
        if (loggedIn != true || !gFFI.userModel.isLogin) {
          return false;
        }
      } else {
        return false;
      }
    }

    // 2. GATE 3: Plan Feature Verification (e.g. Remote Terminal requires Pro+)
    final userPlan = gFFI.userModel.userPlan;
    if (isTerminal) {
      const proPlans = ['pro', 'enterprise', 'superior', 'premium'];
      if (!proPlans.contains(userPlan) && !gFFI.userModel.isAdmin.value) {
        await _showFeatureLockedDialog(
          title: 'Terminal Remoto Silencioso',
          description:
              'O Terminal Remoto em segundo plano (PowerShell/Bash) está disponível a partir do Plano Pro.\n\nFaça upgrade para executar diagnósticos e comandos silenciosos sem interromper a tela do cliente.',
        );
        return false;
      }
    }

    // 3. GATE 2: Daily Quota & Session Initiation Check (/api/session/start)
    final token = bind.mainGetLocalOption(key: 'access_token');
    if (token.isEmpty) {
      return false;
    }

    final rawApi = await bind.mainGetApiServer();
    final apiUrl = rawApi.trim().isNotEmpty ? rawApi.trim() : 'https://zenydesk.com';
    _cachedApiUrl = apiUrl;
    _cachedToken = token;

    try {
      final sessionId = '${peerId}_${DateTime.now().millisecondsSinceEpoch}';
      final response = await http
          .post(
            Uri.parse('$apiUrl/api/session/start'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
            body: jsonEncode({
              'peerId': peerId,
              'sessionId': sessionId,
            }),
          )
          .timeout(const Duration(seconds: 4));

      if (response.statusCode == 403) {
        final Map<String, dynamic> body = jsonDecode(response.body);
        if (body['code'] == 'QUOTA_DAILY_EXCEEDED') {
          await _showQuotaExceededDialog(
            message: body['error'] ??
                'Você atingiu o limite de 2 horas diárias do plano Gratuito hoje.',
          );
          return false;
        }
      }

      if (response.statusCode == 200 || response.statusCode == 201) {
        // Successfully started session on backend -> Start background heartbeat
        _startHeartbeat(apiUrl, sessionId, token);
        return true;
      }
    } catch (e) {
      // Defensive fallback: network glitch or offline fallback should not prevent critical connections
      debugPrint('[ZenydeskGuard] Session start validation bypassed due to network error: $e');
      return true;
    }

    return true;
  }

  /// Dialog shown when technician is not authenticated
  static Future<bool?> _showLoginRequiredDialog() async {
    final completer = Completer<bool?>();
    gFFI.dialogManager.show((setState, close, context) {
      return CustomAlertDialog(
        title: Row(
          children: const [
            Icon(Icons.verified_user_outlined, color: MyTheme.accent, size: 24),
            SizedBox(width: 10),
            Text('Autenticação ZenyDesk', style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text(
              'Para iniciar sessões de suporte remoto e gerenciar máquinas, acesse sua conta ZenyDesk.',
              style: TextStyle(fontSize: 14),
            ),
            SizedBox(height: 8),
            Text(
              'Seus clientes continuam podendo apenas informar o ID e a senha sem necessidade de conta.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              close();
              if (!completer.isCompleted) completer.complete(false);
            },
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: MyTheme.accent,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            ),
            onPressed: () {
              close();
              if (!completer.isCompleted) completer.complete(true);
            },
            child: const Text('Entrar com ZenyDesk'),
          ),
        ],
      );
    });
    return completer.future;
  }

  /// Dialog shown when a feature (e.g. Remote Terminal) is locked for the current plan
  static Future<void> _showFeatureLockedDialog({
    required String title,
    required String description,
  }) async {
    final completer = Completer<void>();
    gFFI.dialogManager.show((setState, close, context) {
      return CustomAlertDialog(
        title: Row(
          children: [
            const Icon(Icons.lock_outline, color: Colors.amber, size: 24),
            const SizedBox(width: 10),
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        content: Text(description, style: const TextStyle(fontSize: 14)),
        actions: [
          TextButton(
            onPressed: () {
              close();
              if (!completer.isCompleted) completer.complete();
            },
            child: const Text('Fechar'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: MyTheme.accent,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            ),
            onPressed: () {
              close();
              launchUrlString('https://zenydesk.com/planos');
              if (!completer.isCompleted) completer.complete();
            },
            child: const Text('Conhecer o Plano Pro'),
          ),
        ],
      );
    });
    return completer.future;
  }

  /// Dialog shown when daily quota is depleted
  static Future<void> _showQuotaExceededDialog({required String message}) async {
    final completer = Completer<void>();
    gFFI.dialogManager.show((setState, close, context) {
      return CustomAlertDialog(
        title: Row(
          children: const [
            Icon(Icons.history_toggle_off_outlined, color: Colors.amber, size: 24),
            SizedBox(width: 10),
            Text('Cota Diária Atingida (2 Horas)', style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(message, style: const TextStyle(fontSize: 14)),
            const SizedBox(height: 10),
            const Text(
              'Para conexões ilimitadas sem interrupções e alta velocidade dedicada, faça o upgrade para o Plano Starter, Pro ou Superior.',
              style: TextStyle(fontSize: 13, color: Colors.grey),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              close();
              if (!completer.isCompleted) completer.complete();
            },
            child: const Text('Fechar'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF10B981),
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            ),
            onPressed: () {
              close();
              launchUrlString('https://zenydesk.com/planos');
              if (!completer.isCompleted) completer.complete();
            },
            child: const Text('Ver Planos e Fazer Upgrade'),
          ),
        ],
      );
    });
    return completer.future;
  }

  /// Manages background heartbeat and notifies server on session end
  static void _startHeartbeat(String apiUrl, String sessionId, String token) {
    stopHeartbeat();
    _activeSessionId = sessionId;

    _heartbeatTimer = Timer.periodic(const Duration(seconds: 60), (timer) async {
      try {
        final resp = await http.post(
          Uri.parse('$apiUrl/api/session/heartbeat'),
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $token',
          },
          body: jsonEncode({'sessionId': sessionId}),
        ).timeout(const Duration(seconds: 5));

        if (resp.statusCode == 200) {
          final data = jsonDecode(resp.body);
          if (data['shouldTerminate'] == true) {
            timer.cancel();
            closeConnection();
            gFFI.dialogManager.show((setState, close, context) {
              return CustomAlertDialog(
                title: Row(
                  children: const [
                    Icon(Icons.timer_off_outlined, color: Colors.redAccent, size: 24),
                    SizedBox(width: 10),
                    Text('Sessão Finalizada', style: TextStyle(fontWeight: FontWeight.bold)),
                  ],
                ),
                content: Text(
                  data['reason'] == 'quota_daily'
                      ? 'Sua cota diária gratuita de 2 horas foi esgotada hoje. Faça upgrade para o Plano Starter ou Pro para conexões ilimitadas.'
                      : 'A sessão atingiu o tempo limite de segurança contínua do servidor e foi encerrada.',
                  style: const TextStyle(fontSize: 14),
                ),
                actions: [
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: MyTheme.accent,
                      foregroundColor: Colors.white,
                    ),
                    onPressed: () {
                      close();
                      launchUrlString('https://zenydesk.com/planos');
                    },
                    child: const Text('Ver Planos'),
                  ),
                ],
              );
            });
          }
        }
      } catch (e) {
        debugPrint('[ZenydeskGuard] Heartbeat warning: $e');
      }
    });
  }

  /// Stops heartbeat and cleanly closes the session on the backend
  static void stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
    final sessionId = _activeSessionId;
    final apiUrl = _cachedApiUrl;
    final token = _cachedToken;

    if (sessionId != null && apiUrl != null && token != null) {
      http.post(
        Uri.parse('$apiUrl/api/session/end'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({'sessionId': sessionId}),
      ).catchError((_) => http.Response('', 500));
      _activeSessionId = null;
    }
  }
}
