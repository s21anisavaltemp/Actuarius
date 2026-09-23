import modules.database as db
import modules.whisper_stt as whisp

# ================= НАСТРОЙКИ =================
# Путь к папке с wav файлами (измените на свой)
DATABASE_PATH = "../database"
REC_FOLDER_PATH = "/home/treadonme/ImportantSyncFolder/NotesBase/Recordings"
TXT_FOLDER_PATH = "/home/treadonme/ImportantSyncFolder/NotesBase/Texts"

# Размер модели (tiny, base, small, medium, large)
MODEL_SIZE = "small"

# Язык аудио (указание языка ускоряет работу и повышает точность)
LANGUAGE = "ru"
# =============================================

def main():
    # Получаем файлы из папки и добавляем в базу имен файлов (как необработанные если их еще не было)
    db.sync_with_folder(DATABASE_PATH, REC_FOLDER_PATH, "wav")
    db.sync_with_folder(DATABASE_PATH, TXT_FOLDER_PATH, "txt")

    # print(db.list_unprocessed(DATABASE_PATH, "wav"))

    # транскрибируем необработанные файлы из папки
    processed_files = whisp.speech_to_text(REC_FOLDER_PATH, TXT_FOLDER_PATH, MODEL_SIZE, LANGUAGE, db.list_unprocessed(DATABASE_PATH, "wav"))
    for filename in processed_files:
        db.mark_processed(DATABASE_PATH, filename, "wav")


    db.sync_with_folder(DATABASE_PATH, REC_FOLDER_PATH, "wav")
    db.sync_with_folder(DATABASE_PATH, TXT_FOLDER_PATH, "txt")



if __name__ == "__main__":
    main()
