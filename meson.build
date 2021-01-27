project('mozo',
  version : '1.25.0',
  meson_version: '>= 0.47.0'
  )

i18n = import('i18n')
python = import('python')
py3 = find_program('python3', required:true)

dependency('libmate-menu', version: '>= 1.21.0')
dependency('pygobject-3.0')

prefix = get_option('prefix')
datadir = join_paths(prefix, get_option('datadir'))

mozo_in = configuration_data()
mozo_in.set('PYTHON', py3.path())
mozo_in.set('PYOPTIONS', '-OOt')

mozo = configure_file(input: 'mozo.in',
  output: 'mozo',
  configuration: mozo_in,
  )

install_data(mozo,
  install_mode: 'rwxr-xr-x',
  install_dir: get_option('bindir')
  )

subdir('po')
subdir('Mozo')
subdir('data')

meson.add_install_script('post_install.py')
