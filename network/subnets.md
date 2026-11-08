# Subnets — 10.20.0.0/16, allocated largest → smallest, smallest prefix that fits

| Subnet | CIDR | Usable range | Broadcast | Usable |
|---|---|---|---|---|
| app | 10.20.0.0/22 | 10.20.0.1 – 10.20.3.254 | 10.20.3.255 | 1,022 (need 1,000) |
| public | 10.20.4.0/24 | 10.20.4.1 – 10.20.4.254 | 10.20.4.255 | 254 (need 250) |
| data | 10.20.5.0/25 | 10.20.5.1 – 10.20.5.126 | 10.20.5.127 | 126 (need 100) |
| management | 10.20.5.128/27 | 10.20.5.129 – 10.20.5.158 | 10.20.5.159 | 30 (need 20) |

Verified with Python `ipaddress` (2026-11-07). No overlap; 10.20.5.160/27
onwards is spare.

# NACL — `network/nacl.json` (stateless: reply traffic needs its own rules)

- The deny for **198.51.100.0/24 is rule 100** in both directions, lower
  than the allow rules — lowest number is checked first, so the deny fires
  even on web ports. Verified: `python3 student_kit/tools/nacl_sim.py
  network/nacl.json student_kit/network/packets_sample.jsonl --check` → 6/6,
  plus 16/16 on extra cases derived from the assignment spec (SSH from
  management, replies from the app subnet, outbound 80/443/8333).
- Inbound: SSH (22) only from the management subnet 10.20.5.128/27
  (rule 110); 80/443 from anywhere (120/130); replies only from the app
  subnet 10.20.0.0/22 on ephemeral ports 1024–65535 (rule 140). Sample
  packet S06 (port 5432 from 10.20.5.20, data subnet) is denied by the
  default deny — no rule matches it.
- Outbound: TCP 8000 only to the app subnet 10.20.0.0/22 (rule 110); then
  rule 115 denies everything else to internal 10.20.0.0/16, so 8000/8333
  to the data, management or public subnets cannot slip through the reply
  rule; replies to clients anywhere on ephemeral ports 1024–65535
  (rule 120). There is deliberately no outbound allow for 80/443/8333.
- Ephemeral ports 1024–65535 are allowed in both directions because a
  stateless NACL must allow reply traffic explicitly; the default (no rule
  matches) is deny.
- Half-page stateless explanation (for the report): a NACL has no memory of
  connections, so unlike a stateful security group it cannot infer that a
  reply packet belongs to an allowed request — every packet, including
  replies, is checked on its own against the rules, which is why the
  ephemeral-port rules above are required.
