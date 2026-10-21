import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/manhua_controller.dart';
import '../models/manhua.dart';
import 'reader_screen.dart';
import 'widgets/add_manhua_dialog.dart';
import 'widgets/download_manhua_dialog.dart';
import 'widgets/edit_manhua_dialog.dart';
import 'widgets/settings_dialog.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _isEditingOrder = false;
  List<Manhua> _editingFavorites = [];
  List<Manhua> _editingOthers = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ManhuaController>().loadManhuas();
    });
  }

  void _enterEditOrderMode(List<Manhua> manhuas) {
    setState(() {
      _isEditingOrder = true;
      _editingFavorites = manhuas.where((m) => m.isFavorite).toList();
      _editingOthers = manhuas.where((m) => !m.isFavorite).toList();
    });
  }

  void _cancelEditOrder() {
    setState(() {
      _isEditingOrder = false;
      _editingFavorites = [];
      _editingOthers = [];
    });
  }

  Future<void> _saveEditOrder() async {
    final controller = context.read<ManhuaController>();
    final orderedIds = [
      ..._editingFavorites.map((m) => m.id),
      ..._editingOthers.map((m) => m.id),
    ];
    setState(() {
      _isEditingOrder = false;
    });
    await controller.saveReorder(orderedIds);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Ordem da lista atualizada com sucesso!'),
          duration: Duration(seconds: 2),
        ),
      );
    }
  }

  void _openReader(Manhua manhua) {
    final controller = context.read<ManhuaController>();
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => ReaderScreen(manhua: manhua)),
    ).then((_) {
      if (mounted) {
        controller.loadManhuas();
      }
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
        title: _isEditingOrder
            ? const Text('Editar Ordem', style: TextStyle(fontWeight: FontWeight.bold))
            : const Row(
                children: [
                  Icon(Icons.auto_stories, color: Color(0xFF8257E6)),
                  SizedBox(width: 10),
                  Text('Manhua Manager', style: TextStyle(fontWeight: FontWeight.bold)),
                ],
              ),
        actions: _isEditingOrder
            ? [
                IconButton(
                  icon: const Icon(Icons.close),
                  tooltip: 'Cancelar',
                  onPressed: _cancelEditOrder,
                ),
                IconButton(
                  icon: const Icon(Icons.check, color: Color(0xFF8257E6)),
                  tooltip: 'Concluir',
                  onPressed: _saveEditOrder,
                ),
              ]
            : [
                IconButton(
                  icon: const Icon(Icons.sort_rounded),
                  tooltip: 'Editar Ordem da Lista',
                  onPressed: controller.manhuas.isEmpty
                      ? null
                      : () => _enterEditOrderMode(controller.manhuas),
                ),
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
      body: Column(
        children: [
          if (controller.isOfflineMode)
            Container(
              width: double.infinity,
              color: const Color(0xFFD97706),
              padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.cloud_off, size: 16, color: Colors.white),
                  SizedBox(width: 8),
                  Text(
                    'Modo Offline: exibindo lista salva localmente',
                    style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
          Expanded(child: _buildBody(controller)),
        ],
      ),
      floatingActionButton: _isEditingOrder
          ? null
          : FloatingActionButton.extended(
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

    if (_isEditingOrder) {
      return _buildReorderList();
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
              side: BorderSide(
                color: manhua.isFavorite
                    ? const Color(0x66F59E0B)
                    : const Color(0xFF323238),
              ),
            ),
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () => _openReader(manhua),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 12.0),
                child: Row(
                  children: [
                    // Botão de Favoritar
                    IconButton(
                      icon: Icon(
                        manhua.isFavorite ? Icons.star : Icons.star_border,
                        color: manhua.isFavorite ? const Color(0xFFF59E0B) : Colors.grey,
                      ),
                      tooltip: manhua.isFavorite ? 'Remover dos favoritos' : 'Favoritar',
                      onPressed: () => controller.toggleFavorite(manhua.id),
                    ),
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
                        if (val == 'download') {
                          showDialog(
                            context: context,
                            builder: (_) => DownloadManhuaDialog(manhua: manhua),
                          );
                        } else if (val == 'edit') {
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
                          value: 'download',
                          child: Row(
                            children: [
                              Icon(Icons.download_rounded, size: 18, color: Color(0xFF8257E6)),
                              SizedBox(width: 8),
                              Text('Downloads Offline'),
                            ],
                          ),
                        ),
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

  Widget _buildReorderList() {
    return CustomScrollView(
      slivers: [
        if (_editingFavorites.isNotEmpty) ...[
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              child: Row(
                children: [
                  const Icon(Icons.star, color: Color(0xFFF59E0B), size: 20),
                  const SizedBox(width: 8),
                  Text(
                    '★ Obras Favoritas (${_editingFavorites.length})',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                      color: Color(0xFFF59E0B),
                    ),
                  ),
                ],
              ),
            ),
          ),
          SliverReorderableList(
            itemCount: _editingFavorites.length,
            onReorderItem: (oldIndex, newIndex) {
              setState(() {
                final item = _editingFavorites.removeAt(oldIndex);
                _editingFavorites.insert(newIndex, item);
              });
            },
            itemBuilder: (context, index) {
              final manhua = _editingFavorites[index];
              return _buildReorderCard(
                key: ValueKey('fav_${manhua.id}'),
                index: index,
                manhua: manhua,
                isFav: true,
              );
            },
          ),
        ],
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Row(
              children: [
                const Icon(Icons.menu_book, color: Colors.grey, size: 20),
                const SizedBox(width: 8),
                Text(
                  _editingFavorites.isNotEmpty
                      ? 'Demais Obras (${_editingOthers.length})'
                      : 'Todas as Obras (${_editingOthers.length})',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                    color: Colors.grey,
                  ),
                ),
              ],
            ),
          ),
        ),
        SliverReorderableList(
          itemCount: _editingOthers.length,
          onReorderItem: (oldIndex, newIndex) {
            setState(() {
              final item = _editingOthers.removeAt(oldIndex);
              _editingOthers.insert(newIndex, item);
            });
          },
          itemBuilder: (context, index) {
            final manhua = _editingOthers[index];
            return _buildReorderCard(
              key: ValueKey('other_${manhua.id}'),
              index: index,
              manhua: manhua,
              isFav: false,
            );
          },
        ),
        const SliverToBoxAdapter(
          child: SizedBox(height: 80),
        ),
      ],
    );
  }

  Widget _buildReorderCard({
    required Key key,
    required int index,
    required Manhua manhua,
    required bool isFav,
  }) {
    return Container(
      key: key,
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Card(
        color: const Color(0xFF202024),
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(
            color: isFav
                ? const Color(0x80F59E0B)
                : const Color(0xFF323238),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Row(
            children: [
              Icon(
                isFav ? Icons.star : Icons.star_border,
                color: isFav ? const Color(0xFFF59E0B) : Colors.grey,
                size: 22,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      manhua.title,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Capítulo ${manhua.currentChapter}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFF8257E6),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              ReorderableDragStartListener(
                index: index,
                child: Container(
                  padding: const EdgeInsets.all(8),
                  child: const Icon(
                    Icons.drag_handle_rounded,
                    color: Colors.grey,
                    size: 26,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
