FROM python:3.12-alpine@sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df

COPY python /opt/taffish-report-render/python
COPY bin/report-render /usr/local/bin/report-render

ENV TAFFISH_ENV=TAFFISH
ENV TAFFISH_NAME=taffish-report-render
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/opt/taffish-report-render/python

RUN chmod +x /usr/local/bin/report-render \
 && test -s /opt/taffish-report-render/python/taffish_report_render/assets/echarts-6.1.0.min.js \
 && test -s /opt/taffish-report-render/python/taffish_report_render/assets/plotly-1.2.0.min.js \
 && test -s /opt/taffish-report-render/python/taffish_report_render/assets/SOURCE.json \
 && test -s /opt/taffish-report-render/python/taffish_report_render/assets/LICENSE.plotly.txt \
 && test -s /opt/taffish-report-render/python/taffish_report_render/runtime_packs/ngl/ngl.js \
 && test -s /opt/taffish-report-render/python/taffish_report_render/runtime_packs/ngl/VERSION \
 && test -s /opt/taffish-report-render/python/taffish_report_render/runtime_packs/igv/igv.min.js \
 && test -s /opt/taffish-report-render/python/taffish_report_render/runtime_packs/igv/VERSION \
 && report-render --version | grep -Fx "taffish-report-render 0.3.3-r1" >/dev/null \
 && python3 -c 'from pathlib import Path; from taffish_report_render.cli import mime_type_for_path; expected={".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".webp":"image/webp",".svg":"image/svg+xml"}; assert all(mime_type_for_path(Path("figure"+suffix)) == mime for suffix,mime in expected.items())' \
 && report-render components > /tmp/taffish-components.txt \
 && grep -F native_subreport_collection /tmp/taffish-components.txt >/dev/null \
 && grep -F interactive_plot /tmp/taffish-components.txt >/dev/null \
 && grep -F structure_viewer /tmp/taffish-components.txt >/dev/null \
 && grep -F tree_viewer /tmp/taffish-components.txt >/dev/null \
 && grep -F sequence_alignment /tmp/taffish-components.txt >/dev/null \
 && grep -F genome_browser /tmp/taffish-components.txt >/dev/null \
 && report-render schema > /tmp/taffish-schema.json \
 && grep -F '"native_subreport_collection"' /tmp/taffish-schema.json >/dev/null \
 && grep -F '"interactive_plot"' /tmp/taffish-schema.json >/dev/null \
 && grep -F '"structure_viewer"' /tmp/taffish-schema.json >/dev/null \
 && grep -F '"tree_viewer"' /tmp/taffish-schema.json >/dev/null \
 && grep -F '"sequence_alignment"' /tmp/taffish-schema.json >/dev/null \
 && grep -F '"genome_browser"' /tmp/taffish-schema.json >/dev/null \
 && grep -F '"media_image_ratio"' /tmp/taffish-schema.json >/dev/null \
 && grep -F '"media_note_layout"' /tmp/taffish-schema.json >/dev/null \
 && grep -F '"note_items"' /tmp/taffish-schema.json >/dev/null \
 && grep -F '"boundary"' /tmp/taffish-schema.json >/dev/null \
 && echo 'b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0  /opt/taffish-report-render/python/taffish_report_render/assets/echarts-6.1.0.min.js' | sha256sum -c - \
 && echo '60169d9df25530f1d5e29c663ceb18ea7492862acb308800fc5ab0f0bf31a41e  /opt/taffish-report-render/python/taffish_report_render/assets/plotly-1.2.0.min.js' | sha256sum -c - \
 && echo 'be8d4b16f1d73458efd70d2a3319ef2888fb6fa821732c319a99ff43a8e4f7e0  /opt/taffish-report-render/python/taffish_report_render/runtime_packs/ngl/ngl.js' | sha256sum -c - \
 && echo 'acf4ee99cdc91be884203930db9c395bc86267552933b483da0b609c16ea05aa  /opt/taffish-report-render/python/taffish_report_render/runtime_packs/igv/igv.min.js' | sha256sum -c - \
 && rm -f /tmp/taffish-components.txt /tmp/taffish-schema.json

WORKDIR /work
