# Exim 4.89 REAL, compilado desde la fuente: CVE-2018-6789 y CVE-2019-10149 (CISA KEV).
# Correo de la muni FICTICIA MuniSoke GT (caso de demo de ReVital). Deliberadamente vulnerable: solo red local / Tailscale.
FROM debian:bookworm-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends gcc make libc6-dev perl libpcre3-dev libdb-dev curl ca-certificates && rm -rf /var/lib/apt/lists/*
ARG URL=https://ftp.exim.org/pub/exim/exim4/old/exim-4.89.tar.gz
ARG SHA256=0ecb90622fac9edea2670e25070a4d4a4879c3fb8541a0b96a880dfac86ccf1c
RUN curl -fsSL -o /tmp/e.tgz "$URL" && echo "$SHA256  /tmp/e.tgz" | sha256sum -c - && tar xzf /tmp/e.tgz -C /tmp
WORKDIR /tmp/exim-4.89
RUN useradd -r -M -d /var/spool/exim -s /usr/sbin/nologin exim \
 && sed -e 's#^BIN_DIRECTORY=.*#BIN_DIRECTORY=/opt/exim/bin#' \
        -e 's#^CONFIGURE_FILE=.*#CONFIGURE_FILE=/opt/exim/etc/configure#' \
        -e 's#^EXIM_USER=.*#EXIM_USER=ref:exim#' \
        -e 's#^SPOOL_DIRECTORY=.*#SPOOL_DIRECTORY=/var/spool/exim#' \
        -e 's#^EXIM_MONITOR=#\# EXIM_MONITOR=#' \
        src/EDITME > Local/Makefile \
 && printf 'USE_DB=yes\nDBMLIB=-ldb\nLOG_FILE_PATH=/var/log/exim/%%slog\nCFLAGS=-O2 -fcommon\n' >> Local/Makefile \
 && make -j"$(nproc)" && make install

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends libpcre3 libdb5.3 netbase && rm -rf /var/lib/apt/lists/* \
 && useradd -r -M -d /var/spool/exim -s /usr/sbin/nologin exim && mkdir -p /var/spool/exim /var/log/exim && chown exim:exim /var/spool/exim /var/log/exim
COPY --from=build /opt/exim /opt/exim
COPY configure /opt/exim/etc/configure
EXPOSE 25
CMD ["/opt/exim/bin/exim", "-bdf", "-q30m"]
