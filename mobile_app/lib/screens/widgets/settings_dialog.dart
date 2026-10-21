import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../controllers/manhua_controller.dart';
import '../../services/download_service.dart';

class SettingsDialog extends StatefulWidget {
  final DownloadService? downloadService;

  const SettingsDialog({super.key, this.downloadService});

  @override
  State<SettingsDialog> createState() => _SettingsDialogState();
}

class _SettingsDialogState extends State<SettingsDialog> {
  late final DownloadService _downloadService;
  late TextEditingController _urlController;
  int _totalDownloadedChapters = 0;

  @override
  void initState() {
    super.initState();
    _downloadService = widget.downloadService ?? DownloadService();
    final controller = context.read<ManhuaController>();
    _urlController = TextEditingController(text: controller.baseUrl);
    _loadDownloadCount();
  }

  Future<void> _loadDownloadCount() async {
    final count = await _downloadService.getTotalDownloadedCount();
    if (mounted) {
      setState(() {
        _totalDownloadedChapters = count;
      });
    }
  }

  Future<void> _confirmClearAllDownloads() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Limpar Todos os Downloads'),
        content: const Text(
          'Deseja realmente excluir todos os capítulos salvos offline do dispositivo? Essa ação não pode ser desfeita.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Excluir Tudo', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await _downloadService.clearAllDownloads();
      await _loadDownloadCount();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Todos os downloads locais foram removidos com sucesso.')),
        );
      }
    }
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
          Text('Configurações'),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
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
                isDense: true,
              ),
            ),
            const Divider(height: 28),
            const Text(
              'Armazenamento Offline',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            Text(
              'Capítulos baixados: $_totalDownloadedChapters',
              style: const TextStyle(fontSize: 13, color: Colors.grey),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.redAccent,
                side: const BorderSide(color: Colors.redAccent),
              ),
              onPressed: _totalDownloadedChapters > 0 ? _confirmClearAllDownloads : null,
              icon: const Icon(Icons.delete_sweep_outlined, size: 18),
              label: const Text('Limpar Todos os Downloads Locais'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Fechar'),
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
          child: const Text('Salvar Servidor'),
        ),
      ],
    );
  }
}
