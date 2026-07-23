from __future__ import annotations

from .io import write_csv


FIELDS = [
    "onet_soc_code",
    "soc_2018_code",
    "title",
    "description",
    "ai_exposure",
    "ai_exposure_source",
    "employment_2024",
    "projected_employment_2024_thousands",
    "projected_employment_2034_thousands",
    "employment_change_2024_2034_pct",
    "annual_openings_2024_2034",
    "median_annual_wage",
    "onet_version",
    "wage_vintage",
    "projection_vintage",
    "crosswalk_method",
    "data_quality_flags",
]

TASK_FIELDS = [
    "onet_soc_code",
    "task_id",
    "task_statement",
    "task_type",
    "incumbents_responding",
    "task_date",
    "domain_source",
    "onet_version",
    "source_file",
    "task_quality_flags",
]


def demo_rows() -> list[dict[str, object]]:
    occupations = [
        (
            "15-1252.00",
            "15-1252",
            "Software Developers",
            1.35,
            1629000,
            1629.0,
            1920.0,
            17.9,
            115700,
            133080,
        ),
        (
            "13-2011.00",
            "13-2011",
            "Accountants and Auditors",
            0.52,
            1450000,
            1450.0,
            1540.0,
            6.0,
            124200,
            81490,
        ),
        (
            "29-1141.00",
            "29-1141",
            "Registered Nurses",
            0.18,
            3568000,
            3568.0,
            3746.0,
            5.0,
            177500,
            86200,
        ),
        (
            "11-2021.00",
            "11-2021",
            "Marketing Managers",
            0.76,
            321000,
            321.0,
            343.0,
            7.0,
            314700,
            161030,
        ),
        (
            "25-2021.00",
            "25-2021",
            "Business Teachers, Postsecondary",
            0.31,
            95000,
            95.0,
            102.0,
            7.0,
            7700,
            80900,
        ),
        (
            "41-2031.00",
            "41-2031",
            "Retail Salespersons",
            0.22,
            4000000,
            4000.0,
            4040.0,
            1.0,
            586000,
            34980,
        ),
        (
            "27-1024.00",
            "27-1024",
            "Graphic Designers",
            0.88,
            265000,
            265.0,
            271.0,
            2.0,
            21700,
            61200,
        ),
        (
            "43-4051.00",
            "43-4051",
            "Customer Service Representatives",
            0.41,
            2900000,
            2900.0,
            2755.0,
            -5.0,
            389000,
            40580,
        ),
    ]
    rows = []
    for (
        code,
        soc,
        title,
        exposure,
        emp,
        projected_2024,
        projected_2034,
        change,
        openings,
        wage,
    ) in occupations:
        rows.append(
            {
                "onet_soc_code": code,
                "soc_2018_code": soc,
                "title": title,
                "description": f"Demo occupation profile for {title}.",
                "ai_exposure": exposure,
                "ai_exposure_source": "demo_aioe",
                "employment_2024": emp,
                "projected_employment_2024_thousands": projected_2024,
                "projected_employment_2034_thousands": projected_2034,
                "employment_change_2024_2034_pct": change,
                "annual_openings_2024_2034": openings,
                "median_annual_wage": wage,
                "onet_version": "30.3-demo",
                "wage_vintage": "May 2025-demo",
                "projection_vintage": "2024-2034-demo",
                "crosswalk_method": "official_soc_bridge_demo",
                "data_quality_flags": "demo_data",
            }
        )
    return rows


def write_demo(path) -> int:
    return write_csv(path, demo_rows(), FIELDS)


def demo_tasks() -> list[dict[str, object]]:
    task_map = {
        "15-1252.00": [
            "Design, develop, and test software applications.",
            "Analyze user needs and recommend software solutions.",
        ],
        "13-2011.00": [
            "Prepare and examine financial records.",
            "Explain accounting findings to managers and clients.",
        ],
        "29-1141.00": [
            "Assess patient health and coordinate care plans.",
            "Communicate treatment information to patients and families.",
        ],
        "11-2021.00": [
            "Plan marketing activities and evaluate campaign performance.",
            "Coordinate marketing strategy with organizational goals.",
        ],
        "25-2021.00": [
            "Teach courses and evaluate student learning.",
            "Prepare instructional materials and lead classroom discussion.",
        ],
        "41-2031.00": [
            "Assist customers with purchases and product questions.",
            "Process sales transactions and maintain merchandise displays.",
        ],
        "27-1024.00": [
            "Develop visual concepts for communications and publications.",
            "Use design principles to create or revise visual materials.",
        ],
        "43-4051.00": [
            "Respond to customer questions about products or services.",
            "Record customer interactions and resolve routine complaints.",
        ],
    }
    rows = []
    for occupation_code, statements in task_map.items():
        for index, statement in enumerate(statements, start=1):
            rows.append(
                {
                    "onet_soc_code": occupation_code,
                    "task_id": f"demo-{occupation_code}-{index}",
                    "task_statement": statement,
                    "task_type": "Core",
                    "incumbents_responding": "demo",
                    "task_date": "demo",
                    "domain_source": "demo",
                    "onet_version": "30.3-demo",
                    "source_file": "demo_task_statements",
                    "task_quality_flags": "demo_data",
                }
            )
    return rows
