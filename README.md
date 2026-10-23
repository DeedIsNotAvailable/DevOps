# Quotes worker — Terraform, SQS и S3

Python-скрапер из первой лабораторной теперь получает задания из SQS.
Chromium открывает https://quotes.toscrape.com/scroll и собирает цитаты из DOM.
Обработчик сохраняет JSON в S3 и **только после успешной записи** удаляет сообщение.
Floci `2.2.0` эмулирует AWS локально, а Terraform создаёт bucket и очередь.
Реальный AWS-аккаунт и платные облачные ресурсы не нужны.

```text
Terraform → S3 bucket + SQS queue во Floci
                         ↑
make run → одно задание → SQS → worker + Chromium → JSON в S3 → удалить сообщение
```

## Окружение

Нужны Docker с Linux Engine, Docker Compose v2+ и GNU Make в Linux/WSL.
Terraform `1.13.5` запускается отдельным контейнером: устанавливать его, AWS CLI,
Python или Chromium на Windows не требуется.

На Windows включите Docker Desktop → Settings → Resources → WSL Integration → Ubuntu.
В Ubuntu установите Make и Git, если их ещё нет.
При проблемах с AmneziaVPN на этой машине используется зеркальная сеть WSL.

Из Ubuntu перейдите в корень репозитория:

```sh
cd /mnt/d/prj/sem7/DevOps
make doctor
make provision
make deploy
make run
```

Из PowerShell те же команды выполняются по отдельности:

```powershell
wsl -d Ubuntu -u root --cd /mnt/d/prj/sem7/DevOps -- make provision
wsl -d Ubuntu -u root --cd /mnt/d/prj/sem7/DevOps -- make deploy
wsl -d Ubuntu -u root --cd /mnt/d/prj/sem7/DevOps -- make run
```

Если используете обычного пользователя Ubuntu, уберите `-u root`.
Все команды Docker и Terraform проекта находятся в Makefile.

## Основные команды

| Команда | Действие |
| --- | --- |
| `make provision` | Запускает Floci, проверяет готовность S3/SQS API, выполняет Terraform init/apply и получает outputs |
| `make deploy` | Собирает образ и запускает worker с параметрами созданных ресурсов; ждёт его готовности |
| `make run` | Отправляет ровно одно задание, ждёт JSON в S3 и удаления сообщения, скачивает результат в out/ |
| `make verify` | Повторно проверяет объект S3 и отсутствие последнего сообщения, включая in-flight |
| `make plan` | Показывает план относительно текущей локальной инфраструктуры |
| `make status` | Показывает контейнеры, bucket, очередь и сообщения |
| `make logs` | Показывает последние логи worker и Floci |
| `make build` | Собирает рабочий образ и образ инструментов |
| `make test` | Проверяет порядок записи/подтверждения и поведение при ошибках |
| `make clean` | Удаляет контейнер worker, его образ и out/; сохраняет Floci, ресурсы и Terraform state |
| `make destroy` | Останавливает worker, удаляет ресурсы через Terraform, затем контейнеры и volume Floci |
| `make ci` | В отдельном окружении проверяет fmt, validate и строит Terraform plan без apply |

Повторный `make provision` при неизменной конфигурации не создаёт ресурсы заново.
После него `make plan` должен показывать отсутствие изменений.
`make destroy` безопасно повторять. Он может временно поднять Floci для проверки
оставшегося локального state, но после завершения окружение будет остановлено.

## Результаты и обработка ошибок

По умолчанию Terraform создаёт bucket `quotes-results-lab2` и очередь `quotes-jobs-lab2`.
Каждый запуск `make run` формирует уникальный job_id; объект хранится по ключу
`results/<job_id>.json`. Пустой или неверный JSON считается ошибкой.

В `out/result.json` скачивается копия проверенного объекта из S3,
а `out/last-job.json` содержит идентификатор последнего задания и сообщения.
Основное хранилище результата — S3, наличие локального файла само по себе не доказывает успех.

Worker удаляет сообщение по receipt handle только после успешного put_object.
Ошибка браузера или записи в S3 оставляет задание в очереди; повторная попытка
разрешается через 10 секунд. Обычный visibility timeout — 300 секунд.
Повторная обработка использует тот же ключ S3 и заменяет предыдущий результат.
Сбор одной задачи должен укладываться в visibility timeout; для более долгих
production-задач потребуется продление тайм-аута.

Проверка удаления использует непотребляющий inspection API Floci: он видит
и доступные, и находящиеся в обработке сообщения. В настоящем AWS такого API нет.

## Файлы и настройки

- `infra/*.tf` — AWS provider, bucket, очередь, переменные и outputs.
- `infra/.terraform.lock.hcl` — зафиксированная версия provider и контрольные суммы; коммитится.
- `infra/terraform.tfstate` — локальное состояние; сохраняется между командами и не коммитится.
- `.runtime/terraform-output.json` и `.runtime/app.env` — автоматически полученные параметры подключения.
- `src/scrape.py` — сбор цитат; `worker.py` — обработка очереди; `cloud_cli.py` — отправка и проверка.

Compose передаёт AWS endpoint, регион и демонстрационные ключи `test` через
переменные окружения. Bucket и URL очереди получаются из Terraform outputs.
В общей Docker-сети endpoint — `http://floci:4566`; на хост опубликован
`http://localhost:4566`. Скрипт не зашивает адрес Floci в код.
Floci возвращает URL очереди с именем `floci`, доступным внутри этой сети.

Изменяемые имена ресурсов описаны в `infra/variables.tf`.
Ресурсы сохраняются в именованном volume Floci; удаление volume вне `destroy`
может рассинхронизировать их с Terraform state.
Для учебного bucket разрешён `force_destroy`: destroy удаляет и сохранённые результаты.

В Dockerfile сохраняются независимые стадии установки Python-пакетов и Chromium.
Лёгкая стадия `tools` использует Python-зависимости без установки браузера.
Рабочий образ `runtime` объединяет браузерную среду и Python-пакеты.
Playwright закреплён; системный Chromium устанавливается apt, поэтому его
совместимость проверяется реальным запуском после обновлений.

## CI и разработка

GitHub Actions вызывает `make ci`. Для него создаются отдельный Compose-проект,
случайный опубликованный порт и копия Terraform-конфигурации в `.runtime/ci-infra`.
Локальная инфраструктура и её state не меняются. CI выполняет init с readonly
lock-файлом, fmt -check, validate и plan, затем удаляет своё окружение даже при ошибке.
Plan предусматривает создание ресурсов, но не применяет изменения.

Для локальной правки Terraform используйте `make fmt`, `make plan`, `make provision`.
После изменения Python-кода выполните `make test`, `make deploy`, `make run`.
State, `.terraform/`, `.runtime/`, планы, секреты и `out/` исключены из Git.

PR лабораторной: из `feat/terraform-infra` в `main`; не сливать до защиты.
