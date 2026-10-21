import 'package:flutter/material.dart';
import '../../services/download_service.dart';

class StorageManagementDialog extends StatefulWidget {
  final DownloadService? downloadService;

  const StorageManagementDialog({super.key, this.downloadService});

  @override
  State<StorageManagementDialog> createState() => _StorageManagementDialogState();
}

class _StorageManagementDialogState extends State<StorageManagementDialog> {
  late final DownloadService _downloadService;
  int _totalChapters = 0;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _downloadService = widget.downloadService ?? DownloadService();
    _loadStats();
  }

  Future<void> _loadStats() async {
    final count = await _downloadService.getTotalDownloadedCount();
    if (mounted) {
      setState(() {
        _totalChapters = count;
        _isLoading = false;
      });
    }
  }

  Future<void> _clearAll() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirmar Limpeza'),
        content: const Text(
          'Deseja excluir todos os capítulos baixados de todas as obras? Esta ação liberará espaço no dispositivo e não poderá ser desfeita.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Limpar', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      setState(() => _isLoading = true);
      await _downloadService.clearAllDownloads();
      await _loadStats();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Armazenamento offline limpo com sucesso!')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.save_outlined, color: Color(0xFF8257E6)),
          SizedBox(width: 8),
          Text('Armazenamento Offline', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        ],
      ),
      content: SizedBox(
        width: double.maxFinite,
        child: _isLoading
            ? const Center(
                heightFactor: 2,
                child: CircularProgressIndicator(color: Color(0xFF8257E6)),
              )
            : Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '$_totalChapters capítulos baixados no dispositivo.',
                    style: const TextStyle(fontSize: 14),
                  ),
                  const SizedBox(height: 16),
                  if (_totalChapters > 0)
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.redAccent,
                        foregroundColor: Colors.white,
                        minimumSize: const Size.fromHeight(40),
                      ),
                      onPressed: _clearAll,
                      icon: const Icon(Icons.delete_forever),
                      label: const Text('Limpar Todos os Downloads'),
                    )
                  else
                    const Text(
                      'Nenhum dado salvo localmente no momento.',
                      style: TextStyle(color: Colors.grey, fontSize: 12),
                    ),
                ],
              ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Fechar'),
        ),
      ],
    );
  }
}
