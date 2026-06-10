"""Reusable UI components for the drought monitor dashboard."""

from __future__ import annotations

import reflex as rx


def kpi_card(title: str, value: rx.Var, subtitle: str) -> rx.Component:
    """Sleek KPI metric tracking card with native Reflex color mode toggling."""
    return rx.box(
        rx.text(title, class_name=rx.cond(rx.color_mode == "light", "text-sm font-medium text-slate-500", "text-sm font-medium text-slate-400")),
        rx.heading(value, size="7", class_name=rx.cond(rx.color_mode == "light", "mt-2 text-slate-900 font-bold tracking-tight", "mt-2 text-slate-50 font-bold tracking-tight")),
        rx.text(subtitle, class_name=rx.cond(rx.color_mode == "light", "mt-1 text-xs text-slate-400", "mt-1 text-xs text-slate-500")),
        class_name=rx.cond(
            rx.color_mode == "light",
            "rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-all duration-200 hover:shadow-md hover:border-slate-300",
            "rounded-2xl border border-slate-800 bg-slate-900/50 p-6 shadow-sm backdrop-blur-md transition-all duration-200 hover:shadow-md hover:border-slate-700"
        ),
    )


def section_card(title: str, *children: rx.Component, class_name: str = "") -> rx.Component:
    """Container layout to unify visual height and alignment across dashboard columns."""
    base_light = "rounded-2xl border border-slate-200 bg-white p-6 shadow-sm flex flex-col justify-between"
    base_dark = "rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-sm flex flex-col justify-between"

    return rx.box(
        rx.heading(
            title,
            size="5",
            class_name=rx.cond(rx.color_mode == "light", "mb-4 font-semibold text-slate-900 tracking-tight", "mb-4 font-semibold text-slate-50 tracking-tight")
        ),
        *children,
        class_name=rx.cond(rx.color_mode == "light", f"{base_light} {class_name}".strip(), f"{base_dark} {class_name}".strip()),
    )


def reservoir_donut(chart_data: rx.Var) -> rx.Component:
    """Radial layout for reservoir state tracking distributions with modern semantic dynamic colors."""
    return rx.recharts.pie_chart(
        rx.recharts.pie(
            # Recorremos los datos inyectando celdas con la paleta de colores adaptativa Tremor
            rx.foreach(
                chart_data,
                lambda entry: rx.recharts.cell(
                    fill=rx.cond(
                        entry["status"] == "Good",
                        rx.cond(rx.color_mode == "light", "#10b981", "#34d399"),      # Esmeralda (Estable)
                        rx.cond(
                            entry["status"] == "Moderate",
                            rx.cond(rx.color_mode == "light", "#eab308", "#fde047"),  # Amarillo (Vigilancia)
                            rx.cond(
                                entry["status"] == "Low",
                                rx.cond(rx.color_mode == "light", "#f97316", "#fb923c"), # Naranja (Prealerta)
                                rx.cond(rx.color_mode == "light", "#ef4444", "#f87171")  # Rojo (Crítico/Alerta)
                            )
                        )
                    )
                )
            ),
            data=chart_data,
            data_key="value",
            name_key="status",
            cx="50%",
            cy="50%",
            inner_radius="66%", # Un anillo ligeramente más fino y elegante
            outer_radius="88%",
            padding_angle=4,     # Separación limpia entre sectores
        ),
        rx.recharts.tooltip(),
        rx.recharts.legend(vertical_align="bottom", height=36),
        width="100%",
        height=320,
    )


def province_table(rows: rx.Var) -> rx.Component:
    """Robust data matrix layout featuring conditional color styling variables."""
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Province", class_name=rx.cond(rx.color_mode == "light", "text-slate-600 font-semibold py-3", "text-slate-400 font-semibold py-3")),
                rx.table.column_header_cell("Fill %", class_name=rx.cond(rx.color_mode == "light", "text-slate-600 font-semibold py-3", "text-slate-400 font-semibold py-3")),
                rx.table.column_header_cell("Rain mm", class_name=rx.cond(rx.color_mode == "light", "text-slate-600 font-semibold py-3", "text-slate-400 font-semibold py-3")),
                rx.table.column_header_cell("Deficit mm", class_name=rx.cond(rx.color_mode == "light", "text-slate-600 font-semibold py-3", "text-slate-400 font-semibold py-3")),
                rx.table.column_header_cell("Stress", class_name=rx.cond(rx.color_mode == "light", "text-slate-600 font-semibold py-3", "text-slate-400 font-semibold py-3")),
                class_name=rx.cond(rx.color_mode == "light", "border-b border-slate-200", "border-b border-slate-800"),
            ),
        ),
        rx.table.body(
            rx.foreach(
                rows,
                lambda row: rx.table.row(
                    rx.table.cell(row["province_name"] | row["Province"] | row["province"], class_name="align-middle font-medium"),
                    rx.table.cell(row["avg_fill_pct"] | row["Fill %"] | row["fill_pct"], class_name="align-middle"),
                    rx.table.cell(row["avg_precipitation_mm"] | row["Rain mm"] | row["rain_mm"], class_name="align-middle"),
                    rx.table.cell(row["daily_water_deficit_mm"] | row["Deficit mm"] | row["deficit_mm"], class_name="align-middle"),
                    rx.table.cell(row["hydric_stress_index"] | row["Stress"] | row["stress"], class_name="align-middle"),
                    class_name=rx.cond(
                        rx.color_mode == "light",
                        "hover:bg-slate-50 border-b border-slate-100 transition-colors duration-150",
                        "hover:bg-slate-800/40 border-b border-slate-900 transition-colors duration-150"
                    ),
                ),
            ),
        ),
        class_name=rx.cond(rx.color_mode == "light", "w-full text-sm text-slate-700", "w-full text-sm text-slate-300"),
        variant="surface",
    )