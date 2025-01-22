import streamlit as st
import numpy as np
import pandas as pd
import math
from pathlib import Path


# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title="CRNS Data Dashboard",
    page_icon=":earth_americas:",  # This is an emoji shortcode. Could be a URL too.
)


# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
"""
# CRNS Data Processor (alpha)

A simple Streamlit app to demonstrate exemplary CRNS data processing, for teaching purposes only. This tool is based on the the [Neptoon code](https://www.neptoon.org), which is currently under intensive development. 

*Authors: Daniel Power, Martin Schrön, Steffen Zacharias, Rafael Rosolem*  
*Supported by Helmholtz Centre for Environmental Research, Leipzig, and University of Bristol, UK, and funding from [ENVRINNOV](https://envri.eu/envrinnov/) and [SOMMET](https://www.sommet-project.eu/home).*

## Data source

Let's process some CRNS data. Here is an example of Hydroinnova data, you can download it from here:
"""

with open("data/CRNS-station_data-Hydroinnova-example.zip", "rb") as file:
    btn = st.download_button(
        label=":material/download: Download Hydroinnova CRS1000 data",
        data=file,
        file_name="CRNS-station_data-Hydroinnova-example.zip",
        mime="application/x-zip-compressed",
    )

"""
## :material/upload_file: Upload data
"""


@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode("utf-8")


import atexit
import tempfile


def cleanup(temp_file: Path):
    """Remove temporary file if it exists"""
    if isinstance(temp_file, Path) and temp_file.exists():
        temp_file.unlink(missing_ok=True)


import io


def save_uploaded_file(uploaded_file: io.BytesIO):
    """
    Save uploaded file to a temporary location.

    Parameters
    ----------
    uploaded_file : StreamlitUploadedFile
        The uploaded file from Streamlit

    Returns
    -------
    Path
        Path to the saved temporary file
    """
    if uploaded_file is None:
        return None

    suffix = Path(uploaded_file.name).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return Path(tmp_file.name)


uploaded_file = st.file_uploader(
    "Upload data files from your local hard drive:", type={"zip", "csv"}
)
if uploaded_file is not None:

    """
    ## :material/full_stacked_bar_chart: Data format
    """

    sensor_type = st.selectbox(
        "Type of sensor data:",
        ("Hydroinnova/Quaesta"),
    )

    # import pandas as pd
    from pathlib import Path
    from neptoon.workflow.process_with_yaml import (
        ProcessWithYaml,
    )
    from neptoon.config import ConfigurationManager

    config = ConfigurationManager()

    if sensor_type == "Hydroinnova/Quaesta":
        sensor_config_path = Path.cwd() / "config" / "A101_station.yaml"
        processing_config_path = Path.cwd() / "config" / "v1_processing_method.yaml"

    config.load_configuration(file_path=sensor_config_path)
    config.load_configuration(file_path=processing_config_path)

    yaml_processor = ProcessWithYaml(configuration_object=config)

    temp_file_path = save_uploaded_file(uploaded_file)
    atexit.register(cleanup, temp_file_path)
    yaml_processor.sensor_config.raw_data_parse_options.data_location = (
        temp_file_path  # uploaded_file
    )

    column_names_is = yaml_processor.sensor_config.raw_data_parse_options.column_names
    if isinstance(column_names_is, list):
        column_names_is = ", ".join(column_names_is)
    else:
        column_names_is = ""

    column_names = st.text_input(
        "Specify the column names, separated by comma. Leave empty to guess.",
        column_names_is,
    )
    if column_names != column_names_is:
        column_names_list = [x.strip() for x in column_names.split(",")]
        yaml_processor.sensor_config.raw_data_parse_options.column_names = (
            column_names_list
        )
        st.write("Updated column names")

    col1, col2 = st.columns(2, vertical_alignment="top")

    skip_lines_is = yaml_processor.sensor_config.raw_data_parse_options.skip_lines
    skip_lines = col1.number_input(
        "Skip lines", yaml_processor.sensor_config.raw_data_parse_options.skip_lines
    )
    if skip_lines != skip_lines_is:
        yaml_processor.sensor_config.raw_data_parse_options.skip_lines = skip_lines

    separator_is = yaml_processor.sensor_config.raw_data_parse_options.separator
    separator = col2.segmented_control(
        "Separator",
        [",", ";", "\s+"],
        default=yaml_processor.sensor_config.raw_data_parse_options.separator,
    )
    if separator != separator_is:
        yaml_processor.sensor_config.raw_data_parse_options.separator = separator

    if st.button(":material/read_more: Parse the data!", type="primary"):
        with st.spinner("Creating data table..."):
            yaml_processor.create_data_hub(return_data_hub=False)
            data_hub = yaml_processor.data_hub
            st.write(
                "Parsed {:,.0f} lines and {:.0f} columns of data.".format(
                    len(data_hub.crns_data_frame), len(data_hub.crns_data_frame.columns)
                )
            )
            st.session_state.data_hub = data_hub
            st.session_state.yaml_processor = yaml_processor

if "data_hub" in st.session_state:
    data_hub = st.session_state.data_hub

    """
    ## :material/search_insights: Data inspection
    """

    tab1, tab2 = st.tabs(
        [":material/Table: Raw data table", ":material/show_chart: Plots"]
    )

    tab1.dataframe(data_hub.crns_data_frame)

    selected_columns = tab2.multiselect(
        "Which columns would you like to view?",
        options=data_hub.crns_data_frame.columns,
        default="epithermal_neutrons_cph",
    )

    filtered_data = data_hub.crns_data_frame[selected_columns]

    # st.line_chart(
    #     data_hub.crns_data_frame,
    #     y=selected_columns,
    # )
    import plotly.express as px

    tab2.plotly_chart(
        px.line(filtered_data, y=selected_columns), use_container_width=True
    )


if "yaml_processor" in st.session_state:

    """
    ## :material/trending_down: Incoming cosmic-ray reference
    """
    stations = dict(
        JUNG=(46.55, 7.98),
        SOPO=(-90, 0),
        OULU=(65.0544, 25.4681),
        PSNM=(18.59, 98.49),
        MXCO=(19.8, -99.1781),
        HRMS=(-34.43, 19.23),
    )

    col1, col2 = st.columns(2, vertical_alignment="top")

    nmdbstation_is = (
        st.session_state.yaml_processor.process_config.correction_steps.incoming_radiation.reference_neutron_monitor.station
    )
    nmdbstation = col1.pills(
        "Select a nearby high-energy neutron monitor",
        options=stations.keys(),
        default="JUNG",
    )
    if nmdbstation != nmdbstation_is:
        st.session_state.yaml_processor.process_config.correction_steps.incoming_radiation.reference_neutron_monitor.station = (
            nmdbstation
        )

    import plotly.graph_objects as go

    fig = go.Figure(
        go.Scattergeo(
            lat=[ll[0] for ll in stations.values()],
            lon=[ll[1] for ll in stations.values()],
            marker=dict(color="blue"),
            name="Available stations",
        )
    )
    fig.add_trace(
        go.Scattergeo(
            lat=[stations[nmdbstation][0]],
            lon=[stations[nmdbstation][1]],
            marker=dict(color="orange"),
            name="Selected station",
        )
    )
    fig.add_trace(
        go.Scattergeo(
            lat=[st.session_state.yaml_processor.sensor_config.sensor_info.latitude],
            lon=[st.session_state.yaml_processor.sensor_config.sensor_info.longitude],
            marker=dict(color="red", symbol="star"),
            name="CRNS location",
        )
    )

    # editing the marker
    fig.update_traces(marker_size=10)

    # this projection_type = 'orthographic is the projection which return 3d globe map'
    fig.update_geos(
        projection=dict(
            type="orthographic",
            rotation=dict(
                lat=stations[nmdbstation][0], lon=stations[nmdbstation][1]
            ),  # , roll=15),
        )
    )

    # layout, exporting html and showing the plot
    fig.update_layout(
        height=200,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend=dict(
            yanchor="bottom",
            y=0.0,
        ),
    )

    col2.plotly_chart(fig)

    col11, col12 = col1.columns([2, 1])

    if col11.button(":material/download: Attach cosmic-ray data", type="primary"):
        with st.spinner("Downloading from NMDB..."):
            st.session_state.yaml_processor._attach_nmdb_data()

            (tab1,) = st.tabs([":material/show_chart: Plots"])

            tab1.plotly_chart(
                px.line(
                    st.session_state.yaml_processor.data_hub.crns_data_frame,
                    y="incoming_neutron_intensity",
                ),
                use_container_width=True,
                color_discrete_sequence=["red"],
            )

    with col12.popover(":material/person_raised_hand:"):
        st.markdown(
            ":material/info: The cosmic-ray reference signal is used to correct the CRNS data for incoming variation of particles, e.g. due to solar events or the solar cycle. This reference signal is measured independently by so-called neutron monitors. The signal of a neutron monitor at a similar geomagnetic cutoff-rigidity and altitude compared to the CRNS location represents the incoming flux at the CRNS site in the best way. Please visit the [NMDB station map](http://www01.nmdb.eu/nest/help.php#helpstations) for more information."
        )
        st.markdown(
            ":material/left_click: Select a nearby neutron monitor, so that its data can be downloaded from [NMDB](http://www01.nmdb.eu/nest) and attached to the CRNS data frame. "
        )

    if (
        "incoming_neutron_intensity"
        in st.session_state.yaml_processor.data_hub.crns_data_frame.columns
    ):
        """
        ## :material/vertical_align_center: Corrections
        """

        col7, col8 = st.columns([1, 1])
        pressure_method = col7.segmented_control(
            "Air pressure correction method",
            ["Zreda et al. (2012)"],
        )
        with col8.popover(":material/person_raised_hand:"):
            st.markdown(
                ":material/info: Air pressure represents the mass of air about the sensor. Every meter of air attenuates the cosmic radiations. The factor to correct for this effect is exponential:"
            )
            st.latex(r"C_p = e^{\beta\,(P_0-P_\text{ref})},")
            st.markdown(
                r"where $\beta$ = 0.0076 and $P_\text{ref}$ = 1013 hPa. See [Zreda et al (2012)](https://doi.org/10.5194/hess-16-4079-2012) for details."
            )

        col9, col10 = st.columns([1, 1])
        humidity_method = col9.segmented_control(
            "Air humidity correction method",
            ["Rosolem et al. (2013)"],
        )
        with col10.popover(":material/person_raised_hand:"):
            st.markdown(
                ":material/info: Air humidity represents the number of hydrogen atoms in the air above and around the sensor. They attenuate the cosmic radiation from above and the neutron radiation from the sides. The factor to correct for this effect is linear:"
            )
            st.latex(r"C_h = \alpha\,(h-h_\text{ref}),")
            st.markdown(
                r"where $\alpha$ = 0.0054 and $h_\text{ref}$ = 0 g/m³. See [Rosolem et al (2013)](https://doi.org/10.1175/JHM-D-12-0120.1) for details."
            )

        col11, col12 = st.columns([1, 1])
        incoming_method = col11.segmented_control(
            "Incoming cosmic rays correction method",
            ["Zreda et al. (2012)"],
            key="other",
        )
        with col12.popover(":material/person_raised_hand:"):
            st.markdown(
                ":material/info: Incoming cosmic radiation varies with time and space depending on the solar activity, for instance. The reference signal is measured by neutron monitors and can be used inversely to correct the CRNS neutrons:"
            )
            st.latex(r"C_I = M_\text{ref}/M\,,")
            st.markdown(
                r"where $M$ is neutron neutron monitor data from [NMDB](http://www01.nmdb.eu/nest/) and $M_\text{ref}$ = 159 cps is a normalization factor. See [Zreda et al (2012)](https://doi.org/10.5194/hess-16-4079-2012) for details."
            )

        if st.button(
            ":material/vertical_align_center: Make corrections", type="primary"
        ):
            with st.spinner("Making corrections..."):
                st.session_state.yaml_processor._prepare_static_values()

                # st.session_state.yaml_processor.process_config.correction_steps.air_pressure.method = (
                #     "zreda_2012"
                # )

                st.session_state.yaml_processor._select_corrections()
                st.session_state.yaml_processor._correct_neutrons()


if ("yaml_processor" in st.session_state) and (
    "corrected_epithermal_neutrons"
    in st.session_state.yaml_processor.data_hub.crns_data_frame.columns
):

    data_hub_processed = st.session_state.yaml_processor.data_hub

    tab3, tab4, tab5 = st.tabs(
        [
            ":material/Table: Processed data table",
            ":material/show_chart: Correction factors",
            ":material/show_chart: Corrected neutrons",
        ]
    )

    tab3.dataframe(data_hub_processed.crns_data_frame)

    selected_columns_corr = [
        "atmospheric_pressure_correction",
        "humidity_correction",
        "incoming_neutron_intensity_correction",
    ]

    data_corr_factors = data_hub_processed.crns_data_frame[selected_columns_corr]

    tab4.plotly_chart(
        px.line(data_corr_factors, y=selected_columns_corr),
        use_container_width=True,
    )

    data_hub_processed.crns_data_frame.loc[
        data_hub_processed.crns_data_frame["corrected_epithermal_neutrons"] < 300,
        "corrected_epithermal_neutrons",
    ] = np.nan

    tab5.write(
        "For better visibility, displayed neutrons are smoothed across 24 hours."
    )
    selected_columns_corrn = [
        "epithermal_neutrons_cph",
        "corrected_epithermal_neutrons",
    ]

    data_corr_neutrons = data_hub_processed.crns_data_frame[selected_columns_corrn]

    tab5.plotly_chart(
        px.line(
            data_corr_neutrons.rolling(24 * 4).mean(),
            y=selected_columns_corrn,
        ),
        use_container_width=True,
    )

    data_hub = st.session_state.yaml_processor.data_hub
    from datetime import date, datetime, timezone

    """
    ## :material/adjust: Calibration
    """
    st.write(
        "To convert corrected neutrons to soil moisture, the calibration factor $N_0$ has to be determined. For that, field-average soil moisture needs to be determined independently on a certain day."
    )

    dt_min = data_hub.crns_data_frame.index.min()
    dt_max = data_hub.crns_data_frame.index.max()

    col13, col14 = st.columns([1, 1])
    calib_date = col13.date_input(
        "When did you determine soil moisture?",
        value=dt_min + (dt_max - dt_min) / 2,
        min_value=dt_min,
        max_value=dt_max,
    )
    calib_sm = col14.number_input(
        label="Independently measured soil moisture",
        step=0.01,
        format="%.3f",
        value=0.2,
    )

    matches = data_hub.crns_data_frame.index.get_indexer(
        [pd.to_datetime(calib_date, utc=True)], method="nearest"
    )
    data_calib_N = data_hub.crns_data_frame.iloc[matches]

    calib_N = data_calib_N["corrected_epithermal_neutrons"]
    N0 = calib_N / (0.0808 / (calib_sm + 0.115) + 0.372)
    st.write("Estimated N0 = %.0f" % N0)

    st.session_state.yaml_processor.sensor_config.sensor_info.N0 = N0

    """
    ## :material/water_drop: Conversion to soil moisture
    """

    col16, col17 = st.columns([1, 1])
    conv_method = col16.segmented_control(
        "Conversion method",
        ["Desilets et al. (2010)"],
    )
    with col17.popover(":material/person_raised_hand:"):
        st.markdown(
            ":material/info: Neutrons can be converted to soil moisture with a roughly inverse relationship. It requires information about static offset in the environment and the calibration parameter."
        )
        st.latex(r"\theta = \frac{0.0808}{N/N_0-0.372}-0.115-\theta_\text{offset}\,,")
        st.markdown(
            r"The result is the gravimetric soil moisture in g/g. See [Desilets et al (2010)](https://doi.org/10.1029/2009WR008726) for details."
        )

    if st.button(":material/water_drop: Convert to soil moisture", type="primary"):
        with st.spinner("Converting neutrons to soil moisture..."):
            st.session_state.yaml_processor._produce_soil_moisture_estimates()

if ("yaml_processor" in st.session_state) and (
    "soil_moisture" in st.session_state.yaml_processor.data_hub.crns_data_frame.columns
):

    data_hub = st.session_state.yaml_processor.data_hub
    data_hub.crns_data_frame.loc[
        data_hub.crns_data_frame["soil_moisture"] < 0, "soil_moisture"
    ] = np.nan
    # data_hub.crns_data_frame.loc[
    #     data_hub.crns_data_frame["soil_moisture"] > 0.5, "soil_moisture"
    # ] = np.nan

    tab6, tab7, tab8 = st.tabs(
        [
            ":material/Table: Final data table",
            ":material/show_chart: Soil moisture",
            ":material/show_chart: Measurement depth",
        ]
    )

    tab6.dataframe(data_hub.crns_data_frame)

    selected_columns_sm = ["soil_moisture", "crns_measurement_depth"]

    data_sm = data_hub.crns_data_frame[selected_columns_sm]

    smooth = tab7.slider("Smoothing window in hours", 1, 25, 6)
    tab7.plotly_chart(
        px.line(
            data_sm.rolling(smooth * 4).mean(), y="soil_moisture", range_y=(0, 0.5)
        ),
        use_container_width=True,
    )

    selected_columns_d = "crns_measurement_depth"
    data_depth = data_hub.crns_data_frame[selected_columns_d]

    tab8.write("Representative integrated depth of the CRNS measurement in cm. ")
    tab8.plotly_chart(
        px.line(
            data_sm.rolling(smooth * 4).mean(),
            y="crns_measurement_depth",
            range_y=(0, 50),
        ),
        use_container_width=True,
    )
