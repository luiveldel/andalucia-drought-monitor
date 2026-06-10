"""Andalusia drought monitor — Reflex dashboard (reads marts only)."""

from __future__ import annotations

import reflex as rx
import plotly.express as px
import plotly.graph_objs as go
import pandas as pd

from app.components import kpi_card, province_table, reservoir_donut, section_card
from app.db import load_dashboard_data


class DashboardState(rx.State):
    """Dashboard state backed by marts schema queries."""

    latest_date: str = ""
    avg_fill_pct: float = 0.0
    total_stored_hm3: float = 0.0
    provinces_in_alert: int = 0
    avg_water_deficit_mm: float = 0.0
    reservoir_status: list[dict[str, str | int]] = []
    province_rows: list[dict[str, str | float]] = []
    loading: bool = True
    error_message: str = ""

    @rx.event
    def load_dashboard(self) -> None:
        self.loading = True
        self.error_message = ""
        try:
            payload = load_dashboard_data()
            self.latest_date = payload["latest_date"]
            self.avg_fill_pct = payload["avg_fill_pct"]
            self.total_stored_hm3 = payload["total_stored_hm3"]
            self.provinces_in_alert = payload["provinces_in_alert"]
            self.avg_water_deficit_mm = payload["avg_water_deficit_mm"]
            self.reservoir_status = payload["reservoir_status"]
            self.province_rows = payload["province_rows"]
        except Exception as exc:  # noqa: BLE001
            self.error_message = str(exc)
        finally:
            self.loading = False

    @rx.var
    def andalusia_map_figure(self) -> go.Figure:
        """
        Generates a reliable geographic map of Andalusia.
        Uses a baseline row on initial load to guarantee that Plotly initializes
        a map layout instead of falling back to an empty Cartesian grid.
        """

        enriched_data = []
        if self.province_rows:
            for row in self.province_rows:
                if row.get("lat") is not None and row.get("lon") is not None:
                    enriched_row = {
                        "province": row.get("province"),
                        "lat": float(row["lat"]),
                        "lon": float(row["lon"]),
                        "fill_pct": float(row.get("fill_pct", 0)),
                        "deficit_mm": float(row.get("deficit_mm", 0)),
                        "stress": float(row.get("stress", 0))
                    }
                    enriched_data.append(enriched_row)

        # Esto obliga a Plotly a inicializar el motor geográfico de mapas de inmediato
        if not enriched_data:
            df = pd.DataFrame([{
                "province": "Andalusia", "lat": 37.3, "lon": -4.5,
                "fill_pct": 0.1, "deficit_mm": 0.0, "stress": 0.0
            }])
        else:
            df = pd.DataFrame(enriched_data)

        # Construimos el scatter_geo de forma nativa pasándole el DataFrame estructurado
        fig = px.scatter_geo(
            df,
            lat="lat",
            lon="lon",
            size="fill_pct",
            color="deficit_mm",
            hover_name="province",
            custom_data=["fill_pct", "deficit_mm", "stress"],
            color_continuous_scale="RdYlBu_r",
            size_max=30 if enriched_data else 0, # Hacemos el punto invisible si es la carga inicial
        )

        # Formateo premium del tooltip
        fig.update_traces(
            hovertemplate="<b>%{hovertext}</b><br><br>Fill: %{customdata[0]:.1f}%<br>Deficit: %{customdata[1]:.2f} mm<br>Stress: %{customdata[2]:.2f}<extra></extra>"
        )

        # Forzamos los límites visuales de la proyección sobre el sur de España
        fig.update_geos(
            scope="europe",
            center=dict(lon=-4.5, lat=37.3),
            projection_scale=20,
            showland=True,
            landcolor="rgba(128, 128, 128, 0.08)",
            showocean=True,
            oceancolor="rgba(0, 0, 0, 0)",
            showcountries=True,
            countrycolor="rgba(128, 128, 128, 0.2)",
            showcoastlines=True,
            coastlinecolor="rgba(128, 128, 128, 0.3)",
        )

        # Integración de fondos transparentes para el Dark Mode
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(r=0, t=0, l=0, b=0),
            coloraxis_colorbar=dict(
                title="Deficit (mm)",
                thicknessmode="pixels", thickness=12,
                lenmode="pixels", len=180,
                yanchor="middle", y=0.5
            )
        )
        return fig


def header() -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.heading(
                "Andalusia Drought Monitor",
                size="8",
                class_name=rx.cond(rx.color_mode == "light", "tracking-tight font-bold text-slate-900", "tracking-tight font-bold text-slate-50")
            ),
            rx.text(
                "Gold layer analytics from marts schema",
                class_name=rx.cond(rx.color_mode == "light", "text-slate-500 text-sm", "text-slate-400 text-sm"),
            ),
            spacing="1",
            align="start",
        ),
        rx.spacer(),
        rx.hstack(
            rx.vstack(
                rx.text("Latest data", class_name=rx.cond(rx.color_mode == "light", "text-xs text-slate-400 uppercase tracking-wider", "text-xs text-slate-500 uppercase tracking-wider")),
                rx.text(
                    DashboardState.latest_date,
                    class_name=rx.cond(rx.color_mode == "light", "font-semibold text-slate-700", "font-semibold text-slate-300"),
                ),
                align="end",
                spacing="0",
            ),
            rx.color_mode.button(
                variant="outline",
                class_name=rx.cond(rx.color_mode == "light", "border-slate-200 text-slate-700", "border-slate-800 text-slate-300"),
            ),
            rx.button(
                "Refresh",
                on_click=DashboardState.load_dashboard,
                class_name="bg-teal-600 hover:bg-teal-700 text-white font-medium px-4 py-2 rounded-lg shadow-sm transition-colors",
            ),
            spacing="4",
            align="center",
        ),
        width="100%",
        align="center",
        class_name=rx.cond(rx.color_mode == "light", "pb-6 border-b border-slate-200", "pb-6 border-b border-slate-800"),
    )

def kpi_grid() -> rx.Component:
    return rx.grid(
        kpi_card(
            "Average reservoir fill",
            DashboardState.avg_fill_pct.to(str) + "%",
            "Provincial average on latest date",
        ),
        kpi_card(
            "Total stored volume",
            DashboardState.total_stored_hm3.to(str) + " hm3",
            "Sum across monitored provinces",
        ),
        kpi_card(
            "Provinces in drought alert",
            DashboardState.provinces_in_alert,
            "From fact_drought_alert (last 30 days)",
        ),
        kpi_card(
            "Average water deficit",
            DashboardState.avg_water_deficit_mm.to(str) + " mm/day",
            "ET0 minus precipitation",
        ),
        columns=rx.breakpoints(initial="1", sm="2", lg="4"),
        gap="4",
        width="100%",
    )

def main_content() -> rx.Component:
    return rx.vstack(
        header(),
        rx.cond(
            DashboardState.error_message != "",
            rx.callout(
                DashboardState.error_message,
                icon="triangle_alert",
                color="red",
                role="alert",
            ),
        ),
        rx.cond(
            DashboardState.loading,
            rx.center(rx.spinner(size="3", color="teal"), padding="12", width="100%"),
            rx.vstack(
                kpi_grid(),

                # Fila Central: Mapa y Donut perfectamente simétricos en altura
                rx.grid(
                    section_card(
                        "Geographical Drought Deficit Map",
                        rx.box(
                            # CAMBIADO: 'page=' por 'data=' para enlazar la figura correctamente
                            rx.plotly(data=DashboardState.andalusia_map_figure, width="100%", height="100%"),
                            class_name="w-full h-[385px] flex items-center justify-center"
                        ),
                    ),
                    section_card(
                        "Reservoir Status Distribution",
                        rx.box(
                            reservoir_donut(DashboardState.reservoir_status),
                            class_name="w-full h-[385px] flex items-center justify-center"
                        ),
                    ),
                    columns=rx.breakpoints(initial="1", lg="2"),
                    gap="6",
                    width="100%",
                    class_name="items-stretch",
                ),

                # Fila Inferior: Tabla extendida
                rx.grid(
                    section_card(
                        "Provincial Drought Snapshot",
                        province_table(DashboardState.province_rows),
                    ),
                    columns="1",
                    width="100%",
                ),
                spacing="6",
                width="100%",
            ),
        ),
        spacing="6",
        width="100%",
        max_width="1280px",
        padding_y="8",
        padding_x="6",
    )

def index() -> rx.Component:
    return rx.box(
        main_content(),
        class_name=rx.cond(
            rx.color_mode == "light",
            "min-h-screen bg-slate-50 text-slate-900 transition-colors duration-200 flex justify-center",
            "min-h-screen bg-slate-950 text-slate-100 transition-colors duration-200 flex justify-center"
        ),
    )

app = rx.App()
app.add_page(index, on_load=DashboardState.load_dashboard)