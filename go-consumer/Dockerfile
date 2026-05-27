FROM golang:1.22-alpine AS builder

WORKDIR /build

COPY go.mod go.sum ./
RUN go mod download

COPY main.go .
RUN CGO_ENABLED=0 go build -o consumer .

FROM alpine:3.20

RUN apk add --no-cache ca-certificates
COPY --from=builder /build/consumer /consumer

CMD ["/consumer"]
