# Сборка

## Windows: PyInstaller и Inno Setup

Установите Python 3.12 и Inno Setup 6 или 7. Из корня репозитория выполните:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

Чтобы собрать только приложение:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1 -SkipInstaller
```

Application ID и имя активности можно передать параметрами:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1 -DiscordApplicationId "1539198053570060299" -ActivityName "Яндекс Музыка"
```

Сборка в GitHub Actions использует тот же скрипт.

## Сборка со встроенным Python

Этот вариант создаёт нативный запускатель Windows x64 и установщик NSIS. В приложении остаются отдельные папки `app` и `runtime`, системная установка Python не используется.

Нужны Python 3.12 на машине сборки, `pefile`, MinGW-w64 (`gcc` и `windres`), NSIS и Windows embeddable ZIP Python 3.12.10 x64 с python.org.

```bash
python -m pip install pefile
python -m pip download --dest wheels --platform win_amd64 --python-version 312 --implementation cp --abi cp312 --only-binary=:all: -r scripts/requirements-embedded.txt
python tools/build_embedded.py --python-zip python-3.12.10-embed-amd64.zip --wheels wheels --output embedded-output
```

Каталог `embedded-output` должен быть новым. При необходимости задайте пути инструментов параметрами `--cc`, `--windres` и `--makensis`.

Результат: папка `embedded-output/YandexMusicRPC` и `embedded-output/YandexMusicRPC-1.0.0-Setup.exe`. Версии и SHA-256 загруженных библиотек записываются в `BUILD-INFO.json`.

Перед упаковкой скрипт проверяет обязательные файлы приложения, CRC архива `runtime/python312.zip` и наличие модулей кодировок. Повреждённый или неполный архив останавливает сборку.
