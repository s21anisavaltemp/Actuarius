import os
from pathlib import Path
import whisper

# ================= НАСТРОЙКИ =================
# Путь к папке с wav файлами (измените на свой)
REC_FOLDER_PATH = "/home/treadonme/ImportantSyncFolder/NotesBase/Recordings"
TXT_FOLDER_PATH = "/home/treadonme/ImportantSyncFolder/NotesBase/Texts"

# Размер модели (tiny, base, small, medium, large)
MODEL_SIZE = "small"

# Язык аудио (указание языка ускоряет работу и повышает точность)
LANGUAGE = "ru"
# =============================================

def main():
    folder = Path(REC_FOLDER_PATH)

    # Проверка существования папки
    if not folder.exists() or not folder.is_dir():
        print(f"❌ Ошибка: Папка '{REC_FOLDER_PATH}' не найдена или не является директорией.")
        return

    # Загрузка модели (делаем это один раз до цикла, чтобы экономить время)
    print(f"⏳ Загрузка модели Whisper ({MODEL_SIZE})...")
    model = whisper.load_model(MODEL_SIZE)
    print("✅ Модель успешно загружена.\n")

    # Ищем все wav файлы в папке (без рекурсии, регистронезависимо)
    wav_files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() == '.wav']

    if not wav_files:
        print(f"⚠️ В папке '{REC_FOLDER_PATH}' не найдено ни одного .wav файла.")
        return

    print(f"🔎 Найдено файлов для проверки: {len(wav_files)}\n")

    processed_count = 0
    skipped_count = 0
    error_count = 0

    for wav_path in wav_files:
        # Формируем путь для будущего txt файла
        txt_path = Path(TXT_FOLDER_PATH + "/" + wav_path.with_suffix(".txt").name)

        # Проверяем, существует ли уже txt файл
        if txt_path.exists():
            print(f"⏭️  Пропуск (txt уже существует): {wav_path.name}")
            skipped_count += 1
            continue

        print(f"🎙️  Обработка: {wav_path.name} ...")

        try:
            # Транскрибация
            result = model.transcribe(str(wav_path), language=LANGUAGE)
            text = result["text"].strip()

            # Сохранение в txt
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)

            print(f"   ✅ Сохранено: {txt_path.name}")
            processed_count += 1

        except Exception as e:
            print(f"   ❌ Ошибка при обработке {wav_path.name}: {e}")
            error_count += 1

    print("\n" + "="*40)
    print(f"🏁 Работа завершена!")
    print(f"Обработано: {processed_count} | Пропущено: {skipped_count} | Ошибок: {error_count}")

if __name__ == "__main__":
    main()
