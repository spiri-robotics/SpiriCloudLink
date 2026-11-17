# The stock NetBird client, joined to the VPN the robot's Spiri Cloud link
# configures (see spiri-netbird.sh).
FROM netbirdio/netbird:0.83.1
COPY spiri-netbird.sh /usr/local/bin/spiri-netbird
ENTRYPOINT ["/usr/local/bin/spiri-netbird"]
