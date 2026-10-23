import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../controllers/manhua_controller.dart';
import '../../services/download_manager.dart';
import '../../services/download_service.dart';
import '../import_manhua_screen.dart';
import 'active_downloads_dialog.dart';
import 'settings_dialog.dart';
import 'storage_management_dialog.dart';

class AppDrawer extends StatelessWidget {
  final VoidCallback? onEnterEditOrder;
  final VoidCallback? onRefresh;
  final DownloadManager? downloadManager;
  final DownloadService? downloadService;

  const AppDrawer({
    super.key,
    this.onEnterEditOrder,
    this.onRefresh,
    this.downloadManager,
    this.downloadService,
  });

  @override
  Widget build(BuildContext context) {
    ManhuaController? controller;
    try {
      controller = Provider.of<ManhuaController>(context);
    } catch (_) {
      controller = null;
    }

    DownloadManager? manager;
    try {
      manager = downloadManager ?? Provider.of<DownloadManager>(context);
    } catch (_) {
      manager = downloadManager;
    }

    final activeCount = manager?.activeTasks.length ?? 0;
    final isOffline = controller?.isOfflineMode ?? false;

    return Drawer(
      backgroundColor: const Color(0xFF18181B),
      child: SafeArea(
        child: Column(
          children: [
            // Header do Menu
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              decoration: const BoxDecoration(
                color: Color(0xFF202024),
                border: Border(
                  bottom: BorderSide(color: Color(0xFF323238), width: 1),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: const Color(0xFF8257E6).withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Icon(Icons.auto_stories, color: Color(0xFF8257E6), size: 24),
                      ),
                      const SizedBox(width: 10),
                      const Expanded(
                        child: Text(
                          'Manhua Manager',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(
                        isOffline ? Icons.cloud_off : Icons.cloud_done,
                        size: 14,
                        color: isOffline ? const Color(0xFFD97706) : Colors.greenAccent,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        isOffline ? 'Modo Offline' : 'Servidor Conectado',
                        style: TextStyle(
                          fontSize: 12,
                          color: isOffline ? const Color(0xFFD97706) : Colors.grey,
                          fontWeight: isOffline ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Itens de Navegação
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(vertical: 4),
                children: [
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.downloading, color: Color(0xFF8257E6)),
                    title: const Text('Downloads em Andamento', style: TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text(
                      activeCount > 0 ? '$activeCount em andamento' : 'Nenhum download ativo',
                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                    trailing: activeCount > 0
                        ? Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: const Color(0xFF8257E6),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              '$activeCount',
                              style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
                            ),
                          )
                        : null,
                    onTap: () {
                      Navigator.pop(context);
                      showDialog(
                        context: context,
                        builder: (_) => ActiveDownloadsDialog(downloadManager: manager),
                      );
                    },
                  ),
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.folder_special_outlined, color: Color(0xFF8257E6)),
                    title: const Text('Armazenamento Offline', style: TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: const Text('Gerenciar capítulos salvos', style: TextStyle(fontSize: 12, color: Colors.grey)),
                    onTap: () {
                      Navigator.pop(context);
                      showDialog(
                        context: context,
                        builder: (_) => StorageManagementDialog(downloadService: downloadService),
                      );
                    },
                  ),
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.cloud_download_outlined, color: Color(0xFF8257E6)),
                    title: const Text('Importar Obras', style: TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: const Text('Importar de fontes online', style: TextStyle(fontSize: 12, color: Colors.grey)),
                    onTap: () {
                      Navigator.pop(context);
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const ImportManhuaScreen()),
                      );
                    },
                  ),
                  const Divider(color: Color(0xFF323238), indent: 16, endIndent: 16, height: 16),
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.sort_rounded, color: Color(0xFF8257E6)),
                    title: const Text('Organizar Obras', style: TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: const Text('Editar ordem da lista', style: TextStyle(fontSize: 12, color: Colors.grey)),
                    enabled: onEnterEditOrder != null,
                    onTap: () {
                      Navigator.pop(context);
                      onEnterEditOrder?.call();
                    },
                  ),
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.settings_outlined, color: Color(0xFF8257E6)),
                    title: const Text('Configurações', style: TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: const Text('Configurar IP do backend', style: TextStyle(fontSize: 12, color: Colors.grey)),
                    onTap: () {
                      Navigator.pop(context);
                      showDialog(
                        context: context,
                        builder: (_) => const SettingsDialog(),
                      );
                    },
                  ),
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.refresh, color: Color(0xFF8257E6)),
                    title: const Text('Atualizar Lista', style: TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: const Text('Sincronizar com servidor', style: TextStyle(fontSize: 12, color: Colors.grey)),
                    onTap: () {
                      Navigator.pop(context);
                      onRefresh?.call();
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
