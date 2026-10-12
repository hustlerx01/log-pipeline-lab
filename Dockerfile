# Fluent Bit with this repo's config. In compose, Loki host is "loki", set via LOKI_HOST env.
FROM fluent/fluent-bit:3.1.9
COPY fluent-bit/ /fluent-bit/etc/
WORKDIR /fluent-bit/etc
CMD ["/fluent-bit/bin/fluent-bit", "-c", "/fluent-bit/etc/fluent-bit.conf"]
