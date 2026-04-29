"""
Reads results/results.csv, generates PNG charts, writes results/report.md
"""

import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = os.environ.get("RESULTS_DIR", os.path.join(os.path.dirname(__file__), "..", "results"))
CSV_PATH    = os.path.join(RESULTS_DIR, "results.csv")
REPORT_PATH = os.path.join(RESULTS_DIR, "report.md")
PLOTS_DIR   = os.path.join(RESULTS_DIR, "plots")

STRATEGY_LABELS = {
    "cache_aside":   "Cache-Aside",
    "write_through": "Write-Through",
    "write_back":    "Write-Back",
}
SCENARIO_LABELS = {
    "read_heavy":  "Чтение-80%\n(80/20)",
    "balanced":    "Смешанный\n(50/50)",
    "write_heavy": "Запись-80%\n(20/80)",
}
SCENARIO_LABELS_MD = {
    "read_heavy":  "Чтение-80% (80/20)",
    "balanced":    "Смешанный (50/50)",
    "write_heavy": "Запись-80% (20/80)",
}
SCENARIO_KEYS = ["read_heavy", "balanced", "write_heavy"]
STRATEGY_KEYS = ["cache_aside", "write_through", "write_back"]
COLORS        = {"cache_aside": "#4C72B0", "write_through": "#55A868", "write_back": "#C44E52"}


def load_results(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def get(rows: list[dict], strategy: str, scenario: str, field: str) -> float:
    for r in rows:
        if r["strategy"] == strategy and r["scenario"] == scenario:
            return float(r.get(field) or 0)
    return 0.0


def bar_chart(rows, field, title, ylabel, filename, pct=False):
    x = np.arange(len(SCENARIO_KEYS))
    width = 0.25
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, sk in enumerate(STRATEGY_KEYS):
        vals = [get(rows, sk, sc, field) * (100 if pct else 1) for sc in SCENARIO_KEYS]
        bars = ax.bar(x + i * width, vals, width, label=STRATEGY_LABELS[sk], color=COLORS[sk], alpha=0.88)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.01,
                    f"{v:.1f}", ha="center", va="bottom", fontsize=8)
    ax.set_title(title, fontsize=13, pad=12)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x + width)
    ax.set_xticklabels([SCENARIO_LABELS[sc] for sc in SCENARIO_KEYS])
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    path = os.path.join(PLOTS_DIR, filename)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print(f"  saved {path}")


def dirty_keys_chart(rows):
    wb_rows = {r["scenario"]: int(r.get("dirty_keys_at_end") or 0)
               for r in rows if r["strategy"] == "write_back"}
    if not any(wb_rows.values()):
        return False
    scenarios = [SCENARIO_LABELS[sc].replace("\n", " ") for sc in SCENARIO_KEYS]
    vals = [wb_rows.get(sc, 0) for sc in SCENARIO_KEYS]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(scenarios, vals, color=COLORS["write_back"], alpha=0.88)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.01,
                str(v), ha="center", va="bottom", fontsize=9)
    ax.set_title("Write-Back: «грязные» ключи перед финальным сбросом в БД", fontsize=12, pad=10)
    ax.set_ylabel("Количество ключей")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    path = os.path.join(PLOTS_DIR, "writeback_dirty.png")
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print(f"  saved {path}")
    return True


def latency_grouped(rows):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=False)
    for ax, sc in zip(axes, SCENARIO_KEYS):
        vals   = [get(rows, sk, sc, "avg_latency_ms") for sk in STRATEGY_KEYS]
        clrs   = [COLORS[sk] for sk in STRATEGY_KEYS]
        labels = [STRATEGY_LABELS[sk] for sk in STRATEGY_KEYS]
        bars   = ax.bar(labels, vals, color=clrs, alpha=0.88)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.01,
                    f"{v:.2f}", ha="center", va="bottom", fontsize=8)
        ax.set_title(SCENARIO_LABELS[sc].replace("\n", " "), fontsize=11)
        ax.set_ylabel("мс" if ax == axes[0] else "")
        ax.grid(axis="y", alpha=0.3)
        ax.tick_params(axis="x", labelsize=8)
    fig.suptitle("Средняя задержка по стратегии и сценарию", fontsize=13, y=1.02)
    fig.tight_layout()
    path = os.path.join(PLOTS_DIR, "latency_grouped.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {path}")


def build_report(rows: list[dict], has_dirty: bool) -> str:
    lines = []
    lines.append("# Практика 3 — Сравнение стратегий кеширования: результаты\n")

    lines.append("## Конфигурация теста\n")
    lines.append("| Параметр        | Значение |")
    lines.append("|-----------------|----------|")
    lines.append("| Длительность    | 30 с на прогон |")
    lines.append("| Ключей в БД     | 1 000 |")
    lines.append("| Конкурентность  | 20 асинхронных воркеров |")
    lines.append("| Кеш             | Redis 7 |")
    lines.append("| База данных     | PostgreSQL 16 |")
    lines.append("| Всего прогонов  | 9 (3 стратегии × 3 сценария) |")
    lines.append("")

    lines.append("## Описание тестов\n")
    lines.append(
        "Каждый прогон длится 30 секунд. 20 асинхронных воркеров непрерывно генерируют "
        "запросы к одному из 1 000 ключей в случайном порядке. "
        "Соотношение чтений и записей задаётся сценарием:"
    )
    lines.append("")
    lines.append("| Сценарий | Чтения | Записи | Описание |")
    lines.append("|----------|--------|--------|----------|")
    lines.append("| Чтение-80% | 80% | 20% | Типичная read-heavy нагрузка (лента, каталог) |")
    lines.append("| Смешанный  | 50% | 50% | Сбалансированная нагрузка |")
    lines.append("| Запись-80% | 20% | 80% | Write-heavy (аналитика, логирование) |")
    lines.append("")
    lines.append(
        "Перед каждым прогоном БД и кеш очищаются, затем БД засевается 1 000 ключами. "
        "Так обеспечивается одинаковое стартовое состояние для всех трёх стратегий."
    )
    lines.append("")

    lines.append("## Таблица результатов\n")
    lines.append("| Стратегия | Сценарий | Пропускная способность (req/s) | Средняя задержка (мс) | Обращений в БД | Hit rate кеша |")
    lines.append("|-----------|----------|-------------------------------|----------------------|----------------|---------------|")
    for r in rows:
        sl  = {"cache_aside": "Cache-Aside (Lazy Loading)", "write_through": "Write-Through", "write_back": "Write-Back"}.get(r["strategy"], r["strategy"])
        scl = SCENARIO_LABELS_MD.get(r["scenario"], r["scenario"])
        hr  = f"{float(r['cache_hit_rate'])*100:.1f}%"
        lines.append(f"| {sl} | {scl} | {float(r['throughput']):.1f} | {float(r['avg_latency_ms']):.3f} | {r['db_hits']} | {hr} |")
    lines.append("")

    lines.append("## Графики\n")

    lines.append("### Пропускная способность (req/s)\n")
    lines.append("![Throughput](plots/throughput.png)\n")

    lines.append("### Средняя задержка (мс)\n")
    lines.append("![Latency](plots/latency_grouped.png)\n")

    lines.append("### Обращений в БД\n")
    lines.append("![DB Hits](plots/db_hits.png)\n")

    lines.append("### Hit rate кеша (%)\n")
    lines.append("![Cache Hit Rate](plots/hit_rate.png)\n")

    if has_dirty:
        lines.append("### Write-Back: накопление «грязных» ключей\n")
        lines.append("![Dirty keys](plots/writeback_dirty.png)\n")
        lines.append(
            "> «Грязные» ключи — это записи, подтверждённые клиенту, но ещё не сохранённые в PostgreSQL. "
            "При аварийном перезапуске Redis до истечения интервала сброса (5 с) эти данные будут потеряны.\n"
        )

    lines.append("## Выводы\n")

    lines.append("### Для чтения (read-heavy)")
    lines.append(
        "**Write-Through** показывает наименьшее число обращений в БД, потому что каждая запись "
        "сразу же прогревает кеш. Cache-Aside инвалидирует ключ при записи, поэтому следующее "
        "чтение всегда промах — количество DB-чтений выше. "
        "Write-Back даёт самый высокий throughput и минимальную задержку за счёт того, что запись "
        "в БД асинхронна, но при этом накапливает «грязные» ключи.\n"
    )

    lines.append("### Для записи (write-heavy)")
    lines.append(
        "**Write-Back** выигрывает по пропускной способности и задержке. "
        "Запись подтверждается после одного Redis SET без синхронного обращения в БД. "
        "Сбросы в БД происходят пакетами каждые 5 секунд, что резко снижает нагрузку на PostgreSQL. "
        "Цена — надёжность: несохранённые «грязные» ключи теряются при сбое Redis.\n"
    )

    lines.append("### Для смешанной нагрузки (balanced)")
    lines.append(
        "**Write-Through** даёт лучший баланс: чтения быстрые (кеш), "
        "записи консистентны (БД + кеш в одной операции), риска потери данных нет. "
        "Рекомендуется как стратегия по умолчанию для большинства задач.\n"
    )

    lines.append("### Особенности Cache-Aside")
    lines.append(
        "Самая простая реализация и наиболее безопасная с точки зрения консистентности. "
        "Запись сначала идёт в БД, затем ключ инвалидируется. Следующее чтение будет промахом — "
        "нагрузка на БД выше, чем у Write-Through при любом объёме записей. "
        "Хорошо подходит, когда актуальность данных критична, а холодный старт кеша допустим.\n"
    )

    lines.append("### Итоговая таблица выводов\n")
    lines.append("| Нагрузка | Лучшая стратегия | Причина |")
    lines.append("|----------|------------------|---------|")
    lines.append("| Чтение-80%  | Write-Through | Прогревает кеш при записи, меньше обращений в БД |")
    lines.append("| Смешанный   | Write-Through | Консистентность + быстрые чтения, нет «грязного» состояния |")
    lines.append("| Запись-80%  | Write-Back    | Нет синхронного обращения в БД при записи, пакетные сбросы |")

    return "\n".join(lines)


def main() -> None:
    if not os.path.exists(CSV_PATH):
        print(f"ОШИБКА: {CSV_PATH} не найден — сначала запустите бенчмарк.")
        sys.exit(1)

    os.makedirs(PLOTS_DIR, exist_ok=True)

    rows = load_results(CSV_PATH)

    print("Генерация графиков...")
    bar_chart(rows, "throughput",     "Пропускная способность по стратегии и сценарию", "req/s",        "throughput.png")
    bar_chart(rows, "db_hits",        "Обращений в БД по стратегии и сценарию",         "кол-во",       "db_hits.png")
    bar_chart(rows, "cache_hit_rate", "Hit rate кеша по стратегии и сценарию",           "% (0-100)",    "hit_rate.png", pct=True)
    latency_grouped(rows)
    has_dirty = dirty_keys_chart(rows)

    report = build_report(rows, has_dirty)
    with open(REPORT_PATH, "w") as f:
        f.write(report)

    print(f"\nОтчёт сохранён → {REPORT_PATH}")
    print(report)


if __name__ == "__main__":
    main()
