FROM golang:1.24.8-alpine3.21 AS builder

WORKDIR /app

# Copy go mod and sum files
COPY go.mod ./
COPY go.sum ./
RUN go mod download

# Copy the source code
COPY . .

# Build the Go app
RUN go build -o eunomia-demo-factory ./cmd

# Final stage
FROM alpine:3.21

# Update and install minimal dependencies
RUN apk --no-cache upgrade && apk --no-cache add ca-certificates

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /app/eunomia-demo-factory .
# Served at /openapi.yaml and /docs
COPY --from=builder /app/specs ./specs

# Expose the port
EXPOSE 8081 8082

# Command to run
ENTRYPOINT ["./eunomia-demo-factory"]