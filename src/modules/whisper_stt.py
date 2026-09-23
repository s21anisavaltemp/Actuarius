import os
from pathlib import Path
import whisper


def speech_to_text(rec_folder_path: str, txt_folder_path: str, model_size: str, language: str, files_list: list[str]) -> list[str]:
    """
    берет папку и обрабатывает все указанные файлы в ней
    """
    folder = Path(rec_folder_path)
    processed_files = []
    # Проверка существования папки
    if not folder.exists() or not folder.is_dir():
        print(f"❌ Ошибка: Папка '{rec_folder_path}' не найдена или не является директорией.")
        return

    # Загрузка модели (делаем это один раз до цикла, чтобы экономить время)
    print(f"⏳ Загрузка модели Whisper ({model_size})...")
    model = whisper.load_model(model_size)
    print("✅ Модель успешно загружена.\n")

    # Ищем все wav файлы в папке (без рекурсии, регистронезависимо)
    audio_files = [f for f in folder.iterdir() if f.is_file() and f.name in files_list]

    if not audio_files:
        print(f"⚠️ В папке '{rec_folder_path}' не найдено ни одного необработанного аудиофайла.")
        return

    print(f"🔎 Найдено файлов для проверки: {len(audio_files)}\n")

    processed_count = 0
    skipped_count = 0
    error_count = 0

    for wav_path in audio_files:
        # Формируем путь для будущего txt файла
        txt_path = Path(txt_folder_path + "/" + wav_path.with_suffix(".txt").name)

        # Проверяем, существует ли уже txt файл
        if txt_path.exists():
            print(f"⏭️  Пропуск (txt уже существует): {wav_path.name}")
            skipped_count += 1
            continue

        print(f"🎙️  Обработка: {wav_path.name} ...")

        try:
            # Транскрибация
            result = model.transcribe(str(wav_path), language=language)
            text = result["text"].strip()

            # Сохранение в txt
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)

            print(f"   ✅ Сохранено: {txt_path.name}")
            processed_files.append(wav_path.name)
            processed_count += 1

        except Exception as e:
            print(f"   ❌ Ошибка при обработке {wav_path.name}: {e}")
            error_count += 1

    print("\n" + "="*40)
    print(f"🏁 Работа завершена!")
    print(f"Обработано: {processed_count} | Пропущено: {skipped_count} | Ошибок: {error_count}")

    return processed_files
