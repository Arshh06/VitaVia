# ==========================================
# Stage 1: Build Java Application with Maven
# ==========================================
FROM eclipse-temurin:21-jdk-jammy AS builder

WORKDIR /build

# Copy Maven Wrapper and POM first to cache dependencies
COPY pom.xml .
COPY .mvn/ .mvn/
COPY mvnw .
RUN sed -i 's/\r$//' mvnw && chmod +x mvnw && ./mvnw dependency:go-offline -B

# Copy application source code
COPY src/ src/

# Build optimized production fat JAR
RUN ./mvnw package -DskipTests -B

# ==========================================
# Stage 2: Minimal Production JRE Runtime
# ==========================================
FROM eclipse-temurin:21-jre-jammy

WORKDIR /app

# Create unprivileged application user
RUN groupadd -r vitavia && useradd -r -g vitavia vitavia

# Create persistent storage directory for H2 database
RUN mkdir -p /app/data && chown -R vitavia:vitavia /app

# Copy executable jar from builder
COPY --from=builder --chown=vitavia:vitavia /build/target/vitavia-backend-1.0.0.jar /app/app.jar

USER vitavia

# Cloud platforms automatically supply $PORT
ENV PORT=8080
EXPOSE 8080

# Optimized container JVM entrypoint
ENTRYPOINT ["java", "-Djava.security.egd=file:/dev/./urandom", "-XX:MaxRAMPercentage=75.0", "-jar", "/app/app.jar"]
