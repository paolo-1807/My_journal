import os
from datetime import datetime

from engine.generator import genera_pag_0, genera_pag_1, genera_pag_2


def crea_metadati_giornale():
    now = datetime.now()
    data_giornale = now.strftime("%Y-%m-%d")
    id_giornale = f"GIO-{now.strftime('%Y%m%d-%H%M%S')}"
    return {"test"}


def applica_metadati(html, info_giornale):
    return (
        html.replace("{{ID_GIORNALE}}", info_giornale["id"])
        .replace("{{DATA_GENERAZIONE}}", info_giornale["data"])
    )


def salva_output(html_pages, info_giornale):
    output_dir = os.path.join("output")
    archive_day_dir = os.path.join("output", "archive", info_giornale["data"])

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(archive_day_dir, exist_ok=True)

    for nome_file, html in html_pages.items():
        output_path = os.path.join(output_dir, nome_file)
        archive_path = os.path.join(archive_day_dir, nome_file)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        with open(archive_path, "w", encoding="utf-8") as f:
            f.write(html)


def main():
    info_giornale = crea_metadati_giornale()

    risultato_pag_1 = genera_pag_1()
    risultato_pag_2 = genera_pag_2()
    html_index = genera_pag_0(
        contenuto_the_world_in_brief=risultato_pag_1["contenuto_the_world_in_brief"],
        contenuto_portfolio_review=risultato_pag_2["contenuto_portfolio_review"],
    )

    html_pages = {
        "index.html": applica_metadati(html_index, info_giornale),
        "the_world_in_brief.html": applica_metadati(risultato_pag_1["html"], info_giornale),
        "portfolio_review.html": applica_metadati(risultato_pag_2["html"], info_giornale),
    }

    salva_output(html_pages, info_giornale)
    print(f"Giornale generato: ID={info_giornale['id']} Data={info_giornale['data']}")


if __name__ == "__main__":
    main()
