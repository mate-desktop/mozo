icon_files = {
  '16x16': 'hicolor_apps_16x16_mozo.png',
  '22x22': 'hicolor_apps_22x22_mozo.png',
  '24x24': 'hicolor_apps_24x24_mozo.png',
  '32x32': 'hicolor_apps_32x32_mozo.png',
  '48x48': 'hicolor_apps_48x48_mozo.png',
  '256x256': 'hicolor_apps_256x256_mozo.png',
}

icondir = join_paths(datadir, 'icons', 'hicolor')

# Remember to call gtk-update-icon-cache when installing / uninstalling.
foreach size, file : icon_files
    install_data(file,
        install_dir: join_paths(icondir, size, 'apps'),
		rename: '@0@.png'.format(meson.project_name()),
    )
endforeach

