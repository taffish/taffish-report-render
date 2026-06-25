FROM python:3.12-alpine

COPY python /opt/taffish-report-render/python
COPY bin/report-render /usr/local/bin/report-render

ENV TAFFISH_ENV=TAFFISH
ENV TAFFISH_NAME=taffish-report-render
ENV PYTHONPATH=/opt/taffish-report-render/python

RUN chmod +x /usr/local/bin/report-render \
 && test -s /opt/taffish-report-render/python/taffish_report_render/assets/echarts-6.1.0.min.js \
 && test -s /opt/taffish-report-render/python/taffish_report_render/runtime_packs/ngl/ngl.js \
 && test -s /opt/taffish-report-render/python/taffish_report_render/runtime_packs/ngl/VERSION \
 && test -s /opt/taffish-report-render/python/taffish_report_render/runtime_packs/igv/igv.min.js \
 && test -s /opt/taffish-report-render/python/taffish_report_render/runtime_packs/igv/VERSION \
 && report-render --version | grep -F "0.1.0-r1" >/dev/null \
 && report-render components | grep -F native_subreport_collection >/dev/null \
 && report-render components | grep -F interactive_plot >/dev/null \
 && report-render components | grep -F structure_viewer >/dev/null \
 && report-render components | grep -F tree_viewer >/dev/null \
 && report-render components | grep -F sequence_alignment >/dev/null \
 && report-render components | grep -F genome_browser >/dev/null \
 && report-render schema | grep -F '"native_subreport_collection"' >/dev/null \
 && report-render schema | grep -F '"interactive_plot"' >/dev/null \
 && report-render schema | grep -F '"structure_viewer"' >/dev/null \
 && report-render schema | grep -F '"tree_viewer"' >/dev/null \
 && report-render schema | grep -F '"sequence_alignment"' >/dev/null \
 && report-render schema | grep -F '"genome_browser"' >/dev/null

WORKDIR /work
