subdir('icons')

desktop_in = configuration_data()
desktop_in.set('VERSION', meson.project_version())

desktop_file = 'mozo.desktop'
i18n.merge_file(desktop_file,
  input: configure_file(
    input: desktop_file + '.in.in',
    output: desktop_file + '.in',
    configuration : desktop_in,
    ),
  output: desktop_file,
  po_dir: join_paths(meson.source_root(), 'po'),
  type: 'desktop',
  install: true,
  install_dir : join_paths(datadir, 'applications')
  )

install_man('mozo.1')
install_data('mozo.ui', install_dir: join_paths(datadir, meson.project_name()))
