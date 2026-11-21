# SIREC 3.2.1: app Java REAL de la muni FICTICIA MuniSoke GT sobre Tomcat 8.5.19 (Java 8, Debian 9).
# Struts 2.3.31, Spring 5.3.17 y Log4j 2.14.1 a proposito (CISA KEV). Deliberadamente vulnerable: sin salida a internet.
FROM maven:3.8.6-openjdk-8 AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -q -B dependency:go-offline
COPY src ./src
RUN mvn -q -B package -DskipTests

FROM vulhub/tomcat:8.5.19
ENV TZ=America/Guatemala
COPY --from=build /src/target/sirec.war /usr/local/tomcat/webapps/sirec.war
EXPOSE 8080
