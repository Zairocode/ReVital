# ProFTPD 1.3.5 REAL, compilado desde la fuente con mod_copy: CVE-2015-3306 (CISA KEV).
# Caso de demo de ReVital (muni FICTICIA). Deliberadamente vulnerable: solo en red local / Tailscale.
FROM debian:bookworm-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends gcc make libc6-dev curl ca-certificates && rm -rf /var/lib/apt/lists/*
ARG URL=https://ftp.osuosl.org/pub/blfs/conglomeration/proftpd/proftpd-1.3.5.tar.gz
ARG SHA256=c10316fb003bd25eccbc08c77dd9057e053693e6527ffa2ea2cc4e08ccb87715
RUN curl -fsSL -o /tmp/p.tgz "$URL" && echo "$SHA256  /tmp/p.tgz" | sha256sum -c - && tar xzf /tmp/p.tgz -C /tmp
WORKDIR /tmp/proftpd-1.3.5
# -fcommon: el codigo de 2014 no compila con el -fno-common por defecto de gcc >= 10
RUN CFLAGS="-O2 -fcommon" ./configure --prefix=/opt/proftpd --with-modules=mod_copy --disable-ident --disable-ipv6 \
 && make -j"$(nproc)" && make install

FROM debian:bookworm-slim
COPY --from=build /opt/proftpd /opt/proftpd
RUN groupadd -r ftp && useradd -r -g ftp -d /srv/ftp -s /usr/sbin/nologin ftp && mkdir -p /srv/ftp/actas
COPY proftpd.conf /opt/proftpd/etc/proftpd.conf
COPY actas/ /srv/ftp/actas/
EXPOSE 21 30000-30009
CMD ["/opt/proftpd/sbin/proftpd", "--nodaemon"]
