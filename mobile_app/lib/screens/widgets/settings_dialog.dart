import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../controllers/manhua_controller.dart';

class SettingsDialog extends StatefulWidget {
  const SettingsDialog({super.key});

  @override
  State<SettingsDialog> createState() => _SettingsDialogState();
}

class _SettingsDialogState extends State<SettingsDialog> {
  late TextEditingController _urlController;

  @override
  void initState() {
    super.initState();
    final controller = context.read<ManhuaController>();
    _urlController = TextEditingController(text: controller.baseUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.settings, color: Color(0xFF8257E6)),
          SizedBox(width: 8),
          Text('Configurar Servidor'),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Endereço do Backend (IP Tailscale / Local):',
            style: TextStyle(fontSize: 13, color: Colors.grey),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _urlController,
            decoration: const InputDecoration(
              hintText: 'http://100.84.57.79:5000',
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.link),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancelar'),
        ),
        ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF8257E6),
            foregroundColor: Colors.white,
          ),
          onPressed: () async {
            final newUrl = _urlController.text.trim();
            if (newUrl.isNotEmpty) {
              await context.read<ManhuaController>().updateBaseUrl(newUrl);
              if (context.mounted) {
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Servidor atualizado com sucesso!')),
                );
              }
            }
          },
          child: const Text('Salvar'),
        ),
      ],
    );
  }
}
