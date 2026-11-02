# SpiriCloudLink

Links a Spiri robot to its organization's Spiri Cloud: it fetches the
configuration the cloud has for the robot, joins the VPN the cloud configures
(NetBird), and serves the robot's camera to the cloud's Frigate.

It is one SpiriConfig app, [`cloud-link`](cloud-link/), the same on a real Mu
and on a simulated one. Install it from
[Appstore-Spiri_development](https://github.com/spiri-robotics/Appstore-Spiri_development),
or link this checkout into SpiriConfig's appsources to run it from source (see
[Development](#development)). Once it's running, link the robot from its
*Spiri Cloud* page in SpiriConfig.

The cloud side is the Drones app in cloud_deploy, whose `docs/drones-api.md`
is the contract.

## What it does

- **Linking** is the RFC 8628 device grant. On the robot's *Spiri Cloud* page
  the user enters the organization's address (`example.spiri.ca`, or its
  Drones app, `https://drones.example.spiri.ca`). The page shows a code, a
  link and a QR code, and someone signed in to the organization approves it
  from any browser. Nothing calls back to the robot, so this works behind any
  NAT.
- **The credential** never expires, and stays in `cloud-link`'s own volume. It
  is not in the env file, so apps that read the configuration can't use it to
  unlink the robot or read anyone else's.
- **The configuration** is an env file the cloud generates, fetched at start
  and every minute with its ETag, and written to
  `/var/lib/spiri-cloud/cloud.env` on the host. Apps read it with compose's
  `env_file` and treat a missing key as that feature not being set up:

  ```yaml
  env_file:
    - path: /var/lib/spiri-cloud/cloud.env
      required: false
  ```

  Compose reads it when a container is created, so a change reaches an app
  when it's next brought up.
- **Fixed settings.** The app's SpiriConfig settings can fix the cloud address
  and the robot's name, to provision a robot for one organization. The page
  then only asks someone there to approve the link.
- **Unlinking** works from either side. A `401` on fetch means the cloud
  unlinked the robot: the credential and the env file are deleted. Any other
  failure is temporary, and the last good file stays.

**NetBird.** The `netbird` service is the stock NetBird client with a wrapper
([`spiri-netbird.sh`](cloud-link/netbird/spiri-netbird.sh)) that watches the
env file instead of reading it through `env_file`, so linking, relinking and
unlinking reach the VPN within seconds without a restart. Apps that must
follow the link live should do the same. It uses host networking, so the VPN
interface (`wt0`) is in the robot's own network namespace. That works in a
simulated robot's docker-in-docker too: the robot is privileged, so inner
containers get `/dev/net/tun`, and the host kernel's WireGuard is used.

**Video.** Frigate pulls WHEP from `/camera/whep`, port 8889, on the robot's
NetBird address. Two services serve it:

- `camera-whep` ([`camera_whep.py`](cloud-link/camera-whep/camera_whep.py), on
  the SpiriCamera image) mirrors the camera named in the *Camera* setting
  (`./camera1`, i.e. `<robot>/camera1`, by default) and serves it through
  SpiriCamera's WHEP app, only on the robot's loopback. A mirror publishes
  nothing of its own, and each JPEG the camera publishes is encoded to H.264
  once. It's a zenoh app, so it stays on `spirisynq`: only the external half
  of the zenoh-router bridge may use host networking, since that bridge is
  where the robot's zenoh permissions are enforced.
- `mediamtx`, MediaMTX on the host network with no zenoh in it
  ([`mediamtx.yml`](cloud-link/mediamtx/mediamtx.yml)). It pulls
  `camera-whep` while someone is watching and serves it on the robot's own
  addresses, media on one fixed UDP port (8189), relaying the H.264 without
  decoding it.

So no camera app changes for Spiri Cloud. Video is the one thing that leaves a
robot outside zenoh, and NetBird's ACLs, not the zenoh router, are its gate.

## Images

Each directory with a Dockerfile under `cloud-link/` is an image,
`ghcr.io/spiri-robotics/spiricloudlink/<name>`: `cloud-link` (the link and its
page), `netbird`, `camera-whep` and `mediamtx`. `main` publishes `edge`;
release tags (`vX.Y.Z`) publish `X.Y.Z`, `X.Y` and `latest`.

## Development

Link the checkout into SpiriConfig's appsources, and install the app from it
with Up (dev), which builds the images from your working tree:

```console
$ ln -s "$PWD" ~/.local/share/spiriconfig/stores/SpiriCloudLink
$ uvx spiriconfig appstore install SpiriCloudLink/cloud-link
$ uvx spiriconfig docker up cloud-link --dev
```

It needs a robot: a zenoh router and a camera on SpiriSynq.
[SpiriDevelopmentKit](https://github.com/spiri-robotics/SpiriDevelopmentKit)'s
simulated Mu installs it from Appstore-Spiri_development.

Tests and lint, as CI runs them:

```console
$ uvx ruff format --check . && uvx ruff check .
$ uvx --with segno pytest
```
