import asyncio
import pyrogram
import os
import random
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ваши API ID и API HASH
API_ID = 
API_HASH = ""

# Файлы с данными
ACCOUNTS_FILE = "accounts.txt"
NICKNAMES_FILE = "nicknames.txt"
BASE_USERNAMES_FILE = "base_usernames.txt"
BIOS_FILE = "bios.txt"  


AVATAR_FOLDER = "avatars"
DEFAULT_NICKNAME = "default_nickname"

def generate_unique_username(base):
    random_number = random.randint(100000, 999999)
    return f"{base}{random_number}"


def load_data(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = [line.strip() for line in f]
        return data
    except FileNotFoundError:
        logging.error(f"Файл {file_path} не найден.")
        return []
    except Exception as e:
        logging.error(f"Ошибка при чтении файла {file_path}: {e}")
        return []

async def change_profile(api_id, api_hash, phone_number, password=None):
    client = None
    try:
        client = pyrogram.Client("account_" + phone_number, api_id, api_hash)
        await client.connect()
        logging.info(f"Подключились к аккаунту {phone_number}")

        try:
            await client.get_me()
            is_authorized = True
        except pyrogram.errors.exceptions.unauthorized_401.AuthKeyInvalid:
            is_authorized = False
        except Exception as e:
            logging.error(f"Ошибка при проверке авторизации для {phone_number}: {e}")
            is_authorized = False

        if not is_authorized:
            try:
                result = await client.send_code(phone_number)
                phone_code_hash = result.phone_code_hash
                if not phone_code_hash:
                    logging.error(f"Не удалось получить phone_code_hash для {phone_number}")
                    return
            except pyrogram.errors.FloodWait as e:
                logging.warning(f"Слишком много запросов для {phone_number}. Ждем {e.x} секунд.")
                await asyncio.sleep(e.x)
                try:
                    result = await client.send_code(phone_number)
                    phone_code_hash = result.phone_code_hash
                    if not phone_code_hash:
                        logging.error(f"Не удалось получить phone_code_hash для {phone_number} после FloodWait")
                        return
                except Exception as e:
                     logging.error(f"Ошибка при повторной отправке кода для {phone_number}: {e}")
                     return

            except Exception as e:
                logging.error(f"Ошибка при отправке кода для {phone_number}: {e}")
                return

            try:
                code = input(f"Введите код для {phone_number}: ")
                await client.sign_in(phone_number, phone_code_hash=phone_code_hash, phone_code=code)
                logging.info(f"Успешно вошли в аккаунт {phone_number}")

            except pyrogram.errors.SessionPasswordNeeded:
                logging.warning(f"Аккаунт {phone_number} защищен паролем двухфакторной аутентификации.")
                if password:
                    try:
                        await client.sign_in(phone_number, phone_code_hash=phone_code_hash, phone_code=code, password=password)
                        logging.info(f"Успешно вошли в аккаунт {phone_number} с паролем.")
                    except Exception as e:
                        logging.error(f"Ошибка при входе с паролем для {phone_number}: {e}")
                        return
                else:
                    logging.error(f"Необходимо ввести пароль для {phone_number}, но он не предоставлен в accounts.txt.")
                    return
            except Exception as e:
                logging.error(f"Ошибка при входе в аккаунт {phone_number}: {e}")
                return

        
        nicknames = load_data(NICKNAMES_FILE)
        nickname = random.choice(nicknames) if nicknames else None
        try:
            await client.update_profile(first_name=nickname or DEFAULT_NICKNAME)
            logging.info(f"Имя установлено для {phone_number}: {nickname or DEFAULT_NICKNAME}")
            await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"Ошибка при установке имени для {phone_number}: {e}")

        
        base_usernames = load_data(BASE_USERNAMES_FILE)
        base_username = random.choice(base_usernames) if base_usernames else None

        if base_username:
            unique_username = generate_unique_username(base_username)
            try:
                await client.set_username(unique_username)
                logging.info(f"Юзернейм установлен для {phone_number}: {unique_username}")
                await asyncio.sleep(1)
            except pyrogram.errors.UsernameNotModified:
                logging.info(f"Юзернейм для {phone_number} не изменен, так как он уже установлен.")
            except Exception as e:
                logging.error(f"Ошибка при установке юзернейма для {phone_number}: {e}")
        else:
            logging.warning(f"Не удалось получить базовый юзернейм из {BASE_USERNAMES_FILE} для {phone_number}.")

        
        bios = load_data(BIOS_FILE)
        bio = random.choice(bios) if bios else None
        if bio:
            try:
                await client.update_profile(bio=bio)
                logging.info(f"Описание установлено для {phone_number}.")
                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Ошибка при установке описания для {phone_number}: {e}")
        else:
            logging.warning(f"Не удалось получить BIO из {BIOS_FILE} для {phone_number}.")

        
        try:
            avatar_files = [f for f in os.listdir(AVATAR_FOLDER) if os.path.isfile(os.path.join(AVATAR_FOLDER, f))]
            if avatar_files and client:
                avatar_file = random.choice(avatar_files)

                if client:
                    await client.set_profile_photo(photo=os.path.join(AVATAR_FOLDER, avatar_file))
                    logging.info(f"Аватар установлен для {phone_number}.")
                    await asyncio.sleep(1)
                else:
                    logging.warning(f"Клиент имеет значение None перед установкой аватарки для {phone_number}.")
            else:
                logging.warning("Нет аватарок в папке или клиент не инициализирован.")
        except pyrogram.errors.PhotoInvalidDimensions:
            logging.error(f"Ошибка: Некорректные размеры фото для {phone_number}.")
        except Exception as e:
            logging.error(f"Ошибка при установке аватарки для {phone_number}: {e}")

    except Exception as e:
        logging.error(f"Общая ошибка для {phone_number}: {e}")
    finally:
        if client:
            await client.disconnect()
            logging.info(f"Отключились от аккаунта {phone_number}")

async def main():
    try:
        with open(ACCOUNTS_FILE, "r") as f:
            accounts = [line.strip().split(":") for line in f]
    except FileNotFoundError:
        logging.error(f"Файл {ACCOUNTS_FILE} не найден.")
        return
    except Exception as e:
        logging.error(f"Ошибка при чтении файла {ACCOUNTS_FILE}: {e}")
        return

    tasks = []
    for account in accounts:
        try:
            api_id, api_hash, phone_number, *password = account
            password = password[0] if len(password) > 0 else None
            tasks.append(asyncio.create_task(change_profile(int(api_id), api_hash, phone_number, password)))
        except ValueError:
            logging.warning(f"Неверный формат строки аккаунта: {account}. Пропускаем.")
            continue

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())