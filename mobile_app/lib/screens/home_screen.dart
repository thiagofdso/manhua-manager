import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/manhua_controller.dart';
import '../models/manhua.dart';
import 'reader_screen.dart';
import 'widgets/add_manhua_dialog.dart';
import 'widgets/edit_manhua_dialog.dart';
import 'widgets/settings_dialog.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ManhuaController>().loadManhuas();
    });
  }

  void _openReader(Manhua manhua) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => ReaderScreen(manhua: manhua)),
    ).then((_) {
      // Recarrega dados ao voltar do leitor para sincronizar capítulo atual
      context.read<ManhuaController>().loadManhuas();
    });
  }

  void _confirmDelete(Manhua manhua) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Excluir Obra'),
        content: Text('Deseja realmente remover "${manhua.title}" da sua lista?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
            onPressed: () {
              Navigator.pop(ctx);
              context.read<ManhuaController>().deleteManhua(manhua.id);
            },
            child: const Text('Excluir', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<ManhuaController>();

    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.auto_stories, color: Color(0xFF8257E6)),
            SizedBox(width: 10),
            Text('Manhua Manager', style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            tooltip: 'Configurar IP do Backend',
            onPressed: () {
              showDialog(
                context: context,
                builder: (_) => const SettingsDialog(),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Atualizar Lista',
            onPressed: () => controller.loadManhuas(),
          ),
        ],
      ),
      body: _buildBody(controller),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: const Color(0xFF8257E6),
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('Adicionar Obra'),
        onPressed: () {
          showDialog(
            context: context,
            builder: (_) => const AddManhuaDialog(),
          );
        },
      ),
    );
  }

  Widget _buildBody(ManhuaController controller) {
    if (controller.isLoading && controller.manhuas.isEmpty) {
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFF8257E6)),
      );
    }

    if (controller.errorMessage != null && controller.manhuas.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.cloud_off, size: 54, color: Colors.orangeAccent),
              const SizedBox(height: 16),
              const Text(
                'Não foi possível conectar ao servidor backend.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                'Servidor configurado: ${controller.baseUrl}\n${controller.errorMessage}',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 12, color: Colors.grey),
              ),
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF8257E6),
                      foregroundColor: Colors.white,
                    ),
                    onPressed: () => controller.loadManhuas(),
                    icon: const Icon(Icons.refresh),
                    label: const Text('Tentar Novamente'),
                  ),
                  const SizedBox(width: 12),
                  OutlinedButton.icon(
                    onPressed: () {
                      showDialog(
                        context: context,
                        builder: (_) => const SettingsDialog(),
                      );
                    },
                    icon: const Icon(Icons.settings),
                    label: const Text('Alterar IP'),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
    }

    if (controller.manhuas.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.menu_book, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            const Text(
              'Nenhum manhua cadastrado.',
              style: TextStyle(fontSize: 18, color: Colors.grey),
            ),
            const SizedBox(height: 8),
            Text(
              'Servidor ativo em: ${controller.baseUrl}',
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      color: const Color(0xFF8257E6),
      onRefresh: () => controller.loadManhuas(),
      child: ListView.builder(
        padding: const EdgeInsets.only(left: 12, right: 12, top: 12, bottom: 80),
        itemCount: controller.manhuas.length,
        itemBuilder: (context, index) {
          final manhua = controller.manhuas[index];
          return Card(
            color: const Color(0xFF202024),
            elevation: 2,
            margin: const EdgeInsets.only(bottom: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: const BorderSide(color: Color(0xFF323238)),
            ),
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () => _openReader(manhua),
              child: Padding(
                padding: const EdgeInsets.all(14.0),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            manhua.title,
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: const Color(0xFF29292E),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              'Capítulo ${manhua.currentChapter}',
                              style: const TextStyle(
                                fontSize: 13,
                                color: Color(0xFF8257E6),
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    // Botões rápidos de capítulo -1 e +1
                    IconButton(
                      icon: const Icon(Icons.remove_circle_outline, color: Colors.grey),
                      tooltip: 'Capítulo Anterior (-1)',
                      onPressed: manhua.currentChapter > 1
                          ? () => controller.changeChapterDelta(manhua.id, -1)
                          : null,
                    ),
                    IconButton(
                      icon: const Icon(Icons.add_circle_outline, color: Color(0xFF8257E6)),
                      tooltip: 'Próximo Capítulo (+1)',
                      onPressed: () => controller.changeChapterDelta(manhua.id, 1),
                    ),
                    // Botão Leitor
                    IconButton(
                      icon: const Icon(Icons.visibility, color: Colors.white),
                      tooltip: 'Abrir Leitor Contínuo',
                      onPressed: () => _openReader(manhua),
                    ),
                    // Menu com opções de Edição e Exclusão
                    PopupMenuButton<String>(
                      icon: const Icon(Icons.more_vert, color: Colors.grey),
                      onSelected: (val) {
                        if (val == 'edit') {
                          showDialog(
                            context: context,
                            builder: (_) => EditManhuaDialog(manhua: manhua),
                          );
                        } else if (val == 'delete') {
                          _confirmDelete(manhua);
                        }
                      },
                      itemBuilder: (context) => [
                        const PopupMenuItem(
                          value: 'edit',
                          child: Row(
                            children: [
                              Icon(Icons.edit, size: 18),
                              SizedBox(width: 8),
                              Text('Editar'),
                            ],
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'delete',
                          child: Row(
                            children: [
                              Icon(Icons.delete, color: Colors.redAccent, size: 18),
                              SizedBox(width: 8),
                              Text('Excluir', style: TextStyle(color: Colors.redAccent)),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
