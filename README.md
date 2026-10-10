# Quotes scrapper — Python и Chromium

Playwright открывает https://quotes.toscrape.com/scroll в Chromium, ждёт загрузки
цитат через JavaScript и прокручивает страницу до конца. Python-скрипт собирает
текст, автора и теги из DOM, затем сохраняет UTF-8 JSON в `out/result.json`.
Ошибки загрузки прерывают выполнение, а успешный запуск заменяет старый результат.

## Как устроен Dockerfile

```text
                  base: python:3.13-bookworm
                       /              \
      python-deps: pip install      browser: apt install chromium
                       \              /
                        runtime + src/
```

Общая основа — Debian Bookworm с Python 3.13. Две независимые стадии
собираются параллельно BuildKit: одна ставит Python-пакеты в `/opt/venv`, другая —
Chromium и его Linux-библиотеки через apt. Финальная стадия наследует браузерную
среду, копирует виртуальное окружение и добавляет скрипт.
Правка `src/` не сбрасывает кеш установки apt и pip.

Playwright закреплён в `requirements.txt`. Chromium берётся из Debian,
поэтому скрипт явно выбирает `/usr/bin/chromium`. Его версию определяет репозиторий
Debian; совместимость с Playwright нужно проверять при обновлении браузера.

## Локальное окружение и production-сборка

Нужны Docker с Linux Engine/BuildKit, GNU Make и POSIX shell.
На Windows используйте WSL2 с Ubuntu и Docker Desktop:
включите **Settings → Resources → WSL Integration → Ubuntu**,
а в Ubuntu установите Make и Git: `sudo apt-get update && sudo apt-get install -y make git`.
Python и Chromium на хосте для контейнерного запуска не требуются.

Из Ubuntu в папке репозитория:

```sh
cd /mnt/d/prj/sem7/DevOps
make build
make run
make verify
```

`make build` собирает конечный образ `quotes-scrapper:lab1`.
`make run` подключает `out/` хоста к `/app/out` контейнера и запускает скрапер.
`make verify` проверяет непустой JSON, обязательные поля, теги и отсутствие дублей.

На этой машине команды можно вызывать отдельно из PowerShell:

```powershell
wsl -d Ubuntu -u root --cd /mnt/d/prj/sem7/DevOps -- make build
wsl -d Ubuntu -u root --cd /mnt/d/prj/sem7/DevOps -- make run
wsl -d Ubuntu -u root --cd /mnt/d/prj/sem7/DevOps -- make verify
```

Результат находится в `D:\prj\sem7\DevOps\out\result.json`.
Удалять старый JSON перед запуском не нужно. После завершения контейнер удаляется,
но образ и результат остаются. Для обычного пользователя Ubuntu уберите `-u root`.
После изменения скрипта выполните `make build`, чтобы обновить его копию в образе.

## Разработка и CI

Редактируйте `src/scrape.py`, затем выполняйте `make build`, `make run`, `make verify`.
Все Docker-команды проекта находятся в Makefile.

GitHub Actions вызывает `make ci`: сборка → реальный сбор цитат → проверка JSON →
очистка. Логи доступны в GitHub Actions. Проверка обращается к внешнему сайту,
поэтому его недоступность также приводит к ошибке CI.

`make clean` удаляет образ проекта и `out/`, сохраняя кеш сборщика.
После `make ci` результат удалён намеренно; для получения JSON повторите build и run.
`out/`, временные инструменты, Python-кеш и логи исключены из Git.
