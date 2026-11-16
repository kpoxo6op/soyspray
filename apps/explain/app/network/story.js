// The network explainer's chapters as plain data: no Three.js, so the catalog build and the tests read it in Node.
// Written for someone who has never set up a network: each piece of jargon is explained where it first appears,
// and the Words panel repeats it. Facts come from the router's live configuration and the cluster inventory, read
// on 15 Nov 2026. Chapters 12 to 16 are proposals, not the current setup.
//
// A beat is one caption with a camera shot, the things it lights up (focus), up to five labels, the traffic it
// shows and optional layers (ruler, k8s, tailnet, dash). `noChips` hides the cluster's app addresses until
// the story has introduced them. A flow is [path of things, 'ok' | 'no']: 'ok' packets run
// the whole path, 'no' packets are refused and vanish at its last point. `check` marks a "Try it" step.

export const SHOTS = {
  wide: { p: [1, 12.5, 8.5], t: [-1.5, 0.4, -4.8] },
  nat: { p: [6, 6.5, 0.5], t: [-1.2, 0.8, -7.4] },
  street: { p: [0.8, 7, 2.6], t: [-3, 0.3, -5] },
  router: { p: [2.4, 5, -0.6], t: [-1.8, 0.3, -5.2] },
  wan: { p: [7.5, 3.8, -5.2], t: [-0.5, 1.2, -9.4] },
  rack: { p: [3.4, 3.6, 4.6], t: [0.2, 0.3, -0.9] },
  uplink: { p: [4.8, 3.2, -2.2], t: [0, 0.2, -3.8] },
  chips: { p: [0.6, 3.4, 5.2], t: [0.2, 0.9, -0.6] },
  k8s: { p: [4.4, 5.6, 6], t: [0, 1.9, 0] },
  ruler: { p: [0, 5.2, 10.5], t: [0, 0, 3.4] },
  devices: { p: [1.5, 5.6, 0.8], t: [-3.4, 0.2, -5.6] },
  names: { p: [2.5, 7, 6], t: [-1.4, 0.4, -3.4] },
  tailnet: { p: [2, 6.5, 8.5], t: [4.2, 1, -2.5] },
  split: { p: [0.5, 15, 7.5], t: [-0.6, 0, -4.8] },
  lab: { p: [3.6, 4.2, 4.6], t: [0.6, 0.3, -0.8] },
  home: { p: [-1, 5, 1.8], t: [-4.6, 0.2, -3.4] },
  iot: { p: [-0.6, 5.6, -3.2], t: [-4.8, 0.3, -8.2] },
  guest: { p: [3.6, 6.8, -1.2], t: [2.4, 0.2, -7.6] },
  watch: { p: [6.4, 4.6, 4.6], t: [1.4, 0.9, -1.8] },
};

const beat = (text, shot, more = {}) => ({ text, shot, focus: [], labels: [], flows: [], ...more });
const check = (text, shot, more = {}) => beat(text, shot, { ...more, check: true });

export const CHAPTERS = [
  {
    id: 'basics',
    noChips: true,
    title: 'What a network is',
    goal: 'Devices, packets and addresses, with your home as the example.',
    beats: [
      beat('A network lets devices send each other messages. Each message travels in small pieces called packets.', 'wide', {
        focus: ['laptop', 'node1'],
        labels: [['laptop', 'your laptop'], ['node1', 'one of your server computers']],
        flows: [[['laptop', 'router', 'switch', 'node1'], 'ok']],
      }),
      beat('Every device has an address, like a house number, so packets reach the right one.', 'street', {
        focus: ['laptop', 'tv', 'phone'],
        labels: [['laptop', '192.168.20.146'], ['tv', '192.168.20.232'], ['router', '192.168.20.1']],
      }),
      beat('All your devices share one network, like houses on one street. Every address on it starts 192.168.20.', 'wide', {
        focus: ['lanPlate'],
        labels: [['lanPlate', 'your street: 192.168.20']],
      }),
      check('On your laptop, find its address in the network settings. It is the one that starts 192.168.20.', 'street', {
        focus: ['laptop'],
        labels: [['laptop', '192.168.20.146']],
      }),
    ],
  },
  {
    id: 'router',
    noChips: true,
    title: 'The router’s three jobs',
    goal: 'Lending addresses, looking up names and guarding the door.',
    beats: [
      beat('The OpenWrt One router joins your street to the internet. It does three jobs for every device here.', 'router', {
        focus: ['router'],
        labels: [['router', 'OpenWrt One router'], ['internet', 'the internet']],
      }),
      beat('One: it lends out addresses. A new phone asks, and the router lends it a free one. This is called DHCP.', 'router', {
        focus: ['router', 'phone'],
        labels: [['phone', 'may I have an address'], ['router', 'DHCP: take .127']],
        flows: [[['phone', 'router', 'phone'], 'ok']],
      }),
      beat('Two: it turns names into addresses, like a phone book. This is called DNS.', 'router', {
        focus: ['router', 'laptop'],
        labels: [['laptop', 'where is booklore.soyspray.vip'], ['router', 'DNS: here is the number']],
        flows: [[['laptop', 'router', 'laptop'], 'ok']],
      }),
      beat('Three: it guards the door. Its firewall turns away anything from the internet that nobody inside asked for.', 'wan', {
        focus: ['router'],
        labels: [['router', 'firewall'], ['internet', 'uninvited traffic']],
        flows: [[['internet', 'router'], 'no']],
      }),
      check('Open 192.168.20.1 in a browser at home. Under Status, Overview lists the devices the router lent addresses to.', 'router', {
        focus: ['router'],
        labels: [['router', '192.168.20.1']],
      }),
    ],
  },
  {
    id: 'addresses',
    noChips: true,
    title: 'Reading an address',
    goal: 'What 192.168.20.0/24 means and who gets which number.',
    layers: ['ruler'],
    beats: [
      beat('An address is four numbers from 0 to 255. On your street the first three, 192.168.20, are the same for everyone.', 'ruler', {
        ruler: 'all',
        labels: [['ruler0', '192.168.20.0'], ['ruler255', '192.168.20.255']],
      }),
      beat('Only the last number changes, so the street has 256 numbers, 0 to 255. Writing /24 after it says exactly that.', 'ruler', {
        ruler: 'all',
        labels: [['ruler128', '192.168.20.0/24: 256 numbers']],
      }),
      beat('Two are reserved: .0 names the street itself and .255 reaches every device at once. The router lives at .1.', 'ruler', {
        ruler: 'ends',
        labels: [['ruler0', '.0 the street'], ['ruler1', '.1 router'], ['ruler255', '.255 everyone']],
      }),
      beat('.10 to .12 are the three cluster computers and .13 is the cluster’s control address. They never change.', 'ruler', {
        ruler: 'nodes',
        labels: [['ruler11', '.10 to .13 cluster']],
      }),
      beat('.20 to .38 are kept for the cluster’s apps. The router never lends these to anything else.', 'ruler', {
        ruler: 'metallb',
        labels: [['ruler29', '.20 to .38 cluster apps']],
      }),
      beat('.100 to .249 are the lending pool. Phones and laptops borrow one for 12 hours, then ask again.', 'ruler', {
        ruler: 'pool',
        labels: [['ruler174', '.100 to .249 lending pool'], ['ruler146', '.146 laptop'], ['ruler232', '.232 TV']],
      }),
    ],
  },
  {
    id: 'wan',
    title: 'The line in',
    goal: 'One public address shared by the whole house, and the one door left open.',
    beats: [
      beat('The internet arrives on one cable into the router’s WAN port. WAN means the wide world outside your home.', 'wan', {
        focus: ['internet', 'router'],
        labels: [['internet', 'the internet'], ['router', 'WAN port']],
      }),
      beat('Your provider gives the router one public IPv4 address. Inside, your devices use private ones the internet cannot reach.', 'nat', {
        focus: ['router'],
        labels: [['router', 'one public address'], ['laptop', 'private .146']],
      }),
      beat('When the laptop opens a website, the router sends the request out under the public address. This is called NAT.', 'nat', {
        focus: ['router', 'laptop'],
        labels: [['router', 'NAT: notes who asked'], ['laptop', 'laptop']],
        flows: [[['laptop', 'router', 'internet'], 'ok']],
      }),
      beat('Replies come back to the router, which remembers who asked and passes each reply to that device.', 'nat', {
        focus: ['router', 'laptop'],
        labels: [['router', 'reply for .146'], ['laptop', 'laptop']],
        flows: [[['internet', 'router', 'laptop'], 'ok']],
      }),
      beat('A port is a numbered door on an address. Websites use 443. You opened one door from outside: 49160.', 'wan', {
        focus: ['router'],
        labels: [['router', 'port 49160 open'], ['internet', 'everything else dropped']],
      }),
      beat('Door 49160 leads to qBittorrent at .30, your torrent app, so other people’s copies can reach it. The rest is refused.', 'wan', {
        focus: ['chip30'],
        labels: [['chip30', 'qBittorrent .30'], ['router', 'dropped']],
        flows: [[['internet', 'router', 'switch', 'chip30'], 'ok'], [['internet', 'router'], 'no']],
      }),
      beat('Your provider also wants a label, VLAN 10, on that cable. The router adds it to every packet, so you never see it.', 'wan', {
        focus: ['wan'],
        labels: [['wan', 'VLAN 10 label'], ['router', 'adds the label']],
      }),
      beat('Your devices also get public IPv6 addresses. NAT does not cover those; the firewall’s refusal is what protects them.', 'wan', {
        focus: ['router'],
        labels: [['router', 'IPv6: firewall only'], ['internet', 'uninvited IPv6']],
        flows: [[['internet', 'router'], 'no']],
      }),
    ],
  },
  {
    id: 'lan',
    title: 'Wired and Wi-Fi',
    goal: 'The switch, a slow cable to replace, and a Wi-Fi radio that is off.',
    beats: [
      beat('The router has a second port, LAN, for your home. Cable and Wi-Fi devices end up on the same street.', 'router', {
        focus: ['router', 'uplink'],
        labels: [['router', 'LAN side'], ['uplink', 'LAN cable']],
      }),
      beat('The LAN cable runs to the switch in the rack. A switch joins cables and sends each packet only down the right one.', 'uplink', {
        focus: ['switch'],
        labels: [['switch', 'rack switch, 8 ports'], ['uplink', 'LAN cable']],
        flows: [[['router', 'switch', 'node0'], 'ok']],
      }),
      beat('That cable runs at 100 Mb/s today, though the port can do 1000. Torrents and remote photo uploads are held to it.', 'uplink', {
        focus: ['uplink'],
        labels: [['uplink', '100 Mb/s, should be 1000']],
        flows: [[['router', 'switch'], 'ok'], [['switch', 'router'], 'ok']],
      }),
      beat('Cluster computers talk to each other through the switch without using that cable, so they stay fast.', 'rack', {
        focus: ['switch'],
        labels: [['switch', 'stays inside the rack']],
        flows: [[['node0', 'switch', 'node2'], 'ok'], [['node2', 'switch', 'node1'], 'ok']],
      }),
      beat('100 Mb/s usually means a damaged cable or a badly fitted plug. A new cable should bring it to 1000.', 'uplink', {
        focus: ['uplink'],
        labels: [['uplink', 'replace this cable']],
      }),
      beat('Wi-Fi uses only the 2.4 GHz radio, which reaches far but is slow. The faster 5 GHz radio is switched off.', 'devices', {
        focus: ['wifi'],
        labels: [['router', '2.4 GHz on, 5 GHz off'], ['phone', 'phone'], ['laptop', 'laptop']],
        flows: [[['phone', 'router'], 'ok'], [['laptop', 'router'], 'ok']],
      }),
      check('After replacing the cable, Status, Overview on the router page should show the LAN port at 1 Gbit/s, not 100.', 'uplink', {
        focus: ['uplink'],
        labels: [['uplink', '1 Gbit/s']],
      }),
    ],
  },
  {
    id: 'cluster',
    title: 'The cluster’s addresses',
    goal: 'Three computers working as one, and the addresses its apps answer on.',
    beats: [
      beat('Your three cluster computers, node-0, node-1 and node-2, sit at .10, .11 and .12. They work as one team.', 'rack', {
        focus: ['node0', 'node1', 'node2'],
        labels: [['node0', 'node-0 .10'], ['node1', 'node-1 .11'], ['node2', 'node-2 .12']],
      }),
      beat('Commands for the cluster go to .13. That address moves to a working computer if one fails, so the team carries on.', 'chips', {
        focus: ['chip13'],
        labels: [['chip13', 'control .13']],
      }),
      beat('Apps in the cluster get their own addresses from .20 to .38. A helper called MetalLB hands them out.', 'chips', {
        focus: ['chip20', 'chip30', 'chip32', 'chip33', 'chip35', 'chip36'],
        labels: [['chip20', '.20'], ['chip36', '.36']],
      }),
      beat('The front door for websites is .20. Every soyspray.vip site comes in there and is sent on to the right app.', 'chips', {
        focus: ['chip20'],
        labels: [['chip20', 'front door .20']],
      }),
      beat('Some apps have their own: qBittorrent .30, Mosquitto .32, Home Assistant .33, Prometheus .35 and Immich .36.', 'chips', {
        focus: ['chip30', 'chip32', 'chip33', 'chip35', 'chip36'],
        labels: [['chip30', 'qBittorrent', 't'], ['chip32', 'Mosquitto', 'b'], ['chip33', 'Home Assistant', 't'], ['chip35', 'Prometheus', 'b'], ['chip36', 'Immich', 't']],
      }),
      beat('The PiKVM beside them is a remote screen and keyboard for a rack computer. Whoever reaches it controls that computer.', 'rack', {
        focus: ['pikvm'],
        labels: [['pikvm', 'PiKVM']],
      }),
      check('Run ping 192.168.20.13 on your laptop. Whichever cluster computer holds that address answers.', 'chips', {
        focus: ['chip13'],
        labels: [['chip13', '.13 answers']],
        flows: [[['laptop', 'router', 'switch', 'chip13', 'switch', 'router', 'laptop'], 'ok']],
      }),
    ],
  },
  {
    id: 'inside',
    title: 'Inside the cluster',
    goal: 'A second, hidden network for apps, and the small phone book on each computer.',
    layers: ['k8s'],
    beats: [
      beat('Inside the cluster is a second, hidden network. Apps run in boxes called pods, and each pod has its own address.', 'k8s', {
        focus: ['pods0', 'pods1', 'pods2'],
        labels: [['pods1', 'pods']],
      }),
      beat('Pod addresses start 10.233. They exist only inside the cluster; your laptop never sees them.', 'k8s', {
        focus: ['pods0', 'pods1', 'pods2'],
        labels: [['pods1', '10.233.x.x, hidden']],
      }),
      beat('Each computer gets a block of 254 pod addresses. Calico carries pod traffic between computers through the switch.', 'k8s', {
        focus: ['pods0', 'pods2'],
        labels: [['pods0', 'node-0’s block'], ['pods2', 'node-2’s block']],
        flows: [[['pods0', 'node0', 'switch', 'node2', 'pods2'], 'ok']],
      }),
      beat('Pods come and go. A service gives a group of pods one address that stays put, also starting 10.233.', 'k8s', {
        focus: ['services'],
        labels: [['services', 'services: addresses that stay']],
      }),
      beat('Each computer keeps a small phone book at 169.254.25.10. Cluster names it answers; the rest it asks the router.', 'k8s', {
        focus: ['dns0', 'dns1', 'dns2'],
        labels: [['dns1', 'phone book'], ['router', 'asks the router']],
        flows: [[['dns0', 'node0', 'switch', 'router'], 'ok']],
      }),
    ],
  },
  {
    id: 'names',
    title: 'How a name finds a site',
    goal: 'Every step from typing booklore.soyspray.vip to the page arriving.',
    beats: [
      beat('Type booklore.soyspray.vip on the laptop. First the laptop asks the router’s phone book for its address.', 'names', {
        focus: ['laptop', 'router'],
        labels: [['laptop', 'booklore.soyspray.vip'], ['router', 'phone book']],
        flows: [[['laptop', 'router', 'laptop'], 'ok']],
      }),
      beat('The router answers 100.96.77.28, an address of its own that also works away from home. Chapter 9 explains how.', 'names', {
        focus: ['router'],
        labels: [['router', '100.96.77.28']],
      }),
      beat('The router hands that request to the front door at .20. It does this only for web traffic, ports 80 and 443.', 'names', {
        focus: ['router', 'chip20'],
        labels: [['router', 'ports 80 and 443'], ['chip20', 'front door .20']],
        flows: [[['laptop', 'router', 'switch', 'chip20'], 'ok']],
      }),
      beat('The front door reads the name, booklore, and passes the request to the BookLore pod. The reply comes back the same way.', 'k8s', {
        focus: ['chip20', 'pods1'],
        labels: [['chip20', 'reads the name'], ['pods1', 'BookLore pod']],
        layers: ['k8s'],
        flows: [[['chip20', 'node1', 'pods1'], 'ok']],
      }),
      beat('Your home names are answered by the router itself. The address it gives, 100.96.77.28, works only for your devices.', 'names', {
        focus: ['router'],
        labels: [['router', 'your phone book'], ['internet', 'cannot use the answer']],
      }),
      check('Run nslookup booklore.soyspray.vip on the laptop. It should answer 100.96.77.28.', 'names', {
        focus: ['laptop'],
        labels: [['laptop', '100.96.77.28']],
        flows: [[['laptop', 'router', 'laptop'], 'ok']],
      }),
    ],
  },
  {
    id: 'tailscale',
    title: 'Away from home',
    goal: 'Private tunnels that bring your phone home from anywhere.',
    layers: ['tailnet'],
    beats: [
      beat('Tailscale links your own devices through private tunnels, wherever they are. Each gets an address starting 100.', 'tailnet', {
        focus: ['tailnet'],
        labels: [['tailnet', 'Tailscale'], ['awayphone', 'phone on mobile data']],
      }),
      beat('The router tells Tailscale it can reach your whole street. A phone on mobile data reaches home through it.', 'tailnet', {
        focus: ['tailnet', 'router'],
        labels: [['router', 'offers 192.168.20']],
        flows: [[['awayphone', 'tailnet', 'router', 'switch', 'chip20'], 'ok']],
      }),
      beat('The phone uses the router’s phone book too, so the same soyspray.vip links work on the bus.', 'tailnet', {
        focus: ['awayphone'],
        labels: [['awayphone', 'same links'], ['router', 'phone book']],
        flows: [[['awayphone', 'tailnet', 'router', 'tailnet', 'awayphone'], 'ok']],
      }),
      beat('The cluster computers are on Tailscale too, so they stay reachable even if the router’s own Tailscale stops.', 'tailnet', {
        focus: ['node0', 'node1', 'node2'],
        labels: [['node1', 'reachable directly']],
        flows: [[['awayphone', 'tailnet', 'node1'], 'ok']],
      }),
      check('Turn off Wi-Fi on your phone, keep Tailscale on, and open a soyspray.vip site. It should load as at home.', 'tailnet', {
        focus: ['awayphone'],
        labels: [['awayphone', 'Wi-Fi off, Tailscale on']],
        flows: [[['awayphone', 'tailnet', 'router', 'switch', 'chip20'], 'ok']],
      }),
    ],
  },
  {
    id: 'firewalls',
    title: 'Your firewalls today',
    goal: 'The router’s three zones and the cluster’s own rules.',
    beats: [
      beat('A firewall is a list of rules saying which packets may pass. You have two: one in the router, one in the cluster.', 'wide', {
        focus: ['router', 'node0', 'node1', 'node2'],
        labels: [['router', 'router firewall'], ['node1', 'cluster rules']],
      }),
      beat('The router sorts every connection into a zone: home (LAN), internet (WAN) or Tailscale. Each zone has its rules.', 'router', {
        focus: ['router'],
        labels: [['router', 'three zones'], ['internet', 'internet zone'], ['laptop', 'home zone']],
      }),
      beat('Internet zone: nothing gets in uninvited except door 49160. Home zone: everything may go anywhere.', 'wan', {
        focus: ['router'],
        labels: [['router', 'in: refused'], ['laptop', 'home: allowed']],
        flows: [[['internet', 'router'], 'no'], [['laptop', 'router', 'internet'], 'ok']],
      }),
      beat('Tailscale zone: the router lets it go anywhere too, so only Tailscale’s own rules limit what your devices reach.', 'tailnet', {
        focus: ['tailnet'],
        labels: [['tailnet', 'Tailscale zone'], ['pikvm', 'even the PiKVM']],
        layers: ['tailnet'],
        flows: [[['awayphone', 'tailnet', 'router', 'switch', 'pikvm'], 'ok']],
      }),
      beat('The cluster has about 30 rules of its own, called network policies, that limit which pods may talk to which.', 'k8s', {
        focus: ['pods0', 'pods1', 'pods2'],
        labels: [['pods1', 'network policies']],
        layers: ['k8s'],
        flows: [[['pods0', 'node0', 'switch', 'node1', 'pods1'], 'ok'], [['pods2', 'node2', 'switch', 'node1'], 'no']],
      }),
      beat('One cluster app, the voice health check, accepts only the voice speaker at .165. Everything else is turned away.', 'k8s', {
        focus: ['voice', 'chip20'],
        labels: [['voice', 'voice speaker .165'], ['chip20', 'listed ranges only']],
        layers: ['k8s'],
        flows: [[['voice', 'router', 'switch', 'node1', 'pods1'], 'ok']],
      }),
      check('Open Network, then Firewall. General Settings lists the three zones; the Port Forwards tab shows the 49160 rule.', 'router', {
        focus: ['router'],
        labels: [['router', 'Network, Firewall']],
      }),
    ],
  },
  {
    id: 'flat',
    title: 'One flat network',
    goal: 'Why every device seeing every other device is the weak spot today.',
    beats: [
      beat('Today every device on the street can talk to every other one. The robot vacuum could reach node-0 or the PiKVM.', 'wide', {
        focus: ['vacuum'],
        labels: [['vacuum', 'robot vacuum'], ['node0', 'node-0'], ['pikvm', 'PiKVM']],
        flows: [[['vacuum', 'router', 'switch', 'node0'], 'ok'], [['vacuum', 'router', 'switch', 'pikvm'], 'ok']],
      }),
      beat('The bulb, TV and vacuum run software you cannot check. If one is hacked, everything on the street is in reach.', 'devices', {
        focus: ['bulb', 'tv', 'vacuum'],
        labels: [['bulb', 'smart bulb'], ['tv', 'TV'], ['vacuum', 'robot vacuum']],
        flows: [[['tv', 'router', 'laptop'], 'ok'], [['bulb', 'router', 'switch', 'node1'], 'ok']],
      }),
      beat('A visitor on your Wi-Fi joins the same street, right next to the cluster and the router’s settings page.', 'wide', {
        focus: ['phone'],
        labels: [['phone', 'a visitor looks the same'], ['router', 'settings page']],
        flows: [[['phone', 'router'], 'ok'], [['phone', 'router', 'switch', 'node2'], 'ok']],
      }),
      beat('Subnets fix this: separate streets, with the router checking who may cross from one to another.', 'wide', {
        focus: ['router'],
        labels: [['router', 'could check every crossing']],
      }),
    ],
  },
  {
    id: 'split',
    title: 'What subnets could do',
    goal: 'A proposal: lab, home, gadget and guest streets with the router between them.',
    split: true,
    beats: [
      beat('A subnet is a separate street with its own address range. The router stands on every street and decides who crosses.', 'split', {
        focus: ['router'],
        labels: [['router', 'on every street'], ['labPlate', 'lab'], ['homePlate', 'home'], ['iotPlate', 'gadgets'], ['guestPlate', 'guests']],
        guest: true,
      }),
      beat('Keep 192.168.20 for the lab: the cluster, the switch and the PiKVM. No cluster address has to change.', 'lab', {
        focus: ['labPlate'],
        labels: [['labPlate', 'lab 192.168.20'], ['pikvm', 'PiKVM']],
      }),
      beat('Move phones and laptops to a home street, 192.168.30, with its own Wi-Fi name.', 'home', {
        focus: ['homePlate'],
        labels: [['homePlate', 'home 192.168.30'], ['laptop', 'laptop'], ['phone', 'phone']],
      }),
      beat('Put the vacuum, bulb, TV, voice speaker and sensors on a gadget street, 192.168.40. This is often called IoT.', 'iot', {
        focus: ['iotPlate'],
        labels: [['iotPlate', 'gadgets 192.168.40'], ['tv', 'TV'], ['vacuum', 'vacuum'], ['bulb', 'bulb']],
      }),
      beat('Give visitors a guest street, 192.168.50, that reaches the internet and nothing else.', 'guest', {
        focus: ['guestPlate'],
        labels: [['guestPlate', 'guests 192.168.50'], ['guestphone', 'visitor’s phone']],
        guest: true,
      }),
    ],
  },
  {
    id: 'rules',
    title: 'Rules between subnets',
    goal: 'What each street may reach, and what a hacked gadget would still see.',
    split: true,
    beats: [
      beat('Rules say which street may reach which. Home devices may open the websites at .20 and Home Assistant at .33.', 'split', {
        focus: ['homePlate', 'chip20', 'chip33'],
        labels: [['chip20', 'websites .20'], ['chip33', 'Home Assistant .33'], ['phone', 'phone'], ['mac', 'Mac']],
        flows: [[['phone', 'router', 'switch', 'chip20'], 'ok'], [['mac', 'router', 'switch', 'chip33'], 'ok']],
        guest: true,
      }),
      beat('Your laptop gets one more rule: it may reach the cluster computers, so you can still look after them.', 'split', {
        focus: ['laptop', 'node0'],
        labels: [['laptop', 'laptop'], ['node0', 'allowed']],
        flows: [[['laptop', 'router', 'switch', 'node0'], 'ok']],
        guest: true,
      }),
      beat('Gadgets may reach the internet, Mosquitto at .32 and Home Assistant at .33. Nothing else on your network.', 'split', {
        focus: ['iotPlate', 'chip32', 'chip33'],
        labels: [['chip32', 'Mosquitto .32'], ['chip33', 'Home Assistant .33'], ['esp', 'sensor']],
        flows: [[['esp', 'router', 'switch', 'chip32'], 'ok'], [['chip33', 'switch', 'router', 'bulb'], 'ok'], [['vacuum', 'router', 'internet'], 'ok']],
        guest: true,
      }),
      beat('Guests get the internet only. The router refuses a visitor’s phone that tries its settings page or the cluster.', 'guest', {
        focus: ['guestPlate'],
        labels: [['guestphone', 'visitor’s phone'], ['router', 'refused']],
        flows: [[['guestphone', 'router', 'internet'], 'ok'], [['guestphone', 'router'], 'no']],
        guest: true,
      }),
      beat('If the vacuum is hacked now, it reaches Mosquitto, Home Assistant and the internet: not the cluster, PiKVM or laptop.', 'split', {
        focus: ['vacuum'],
        labels: [['vacuum', 'robot vacuum'], ['router', 'refused']],
        flows: [[['vacuum', 'router'], 'no'], [['vacuum', 'router', 'switch', 'chip32'], 'ok']],
        guest: true,
      }),
    ],
  },
  {
    id: 'how',
    title: 'How to get there',
    goal: 'Wi-Fi first, then the cluster’s lists, then a better switch if cables must split too.',
    split: true,
    beats: [
      beat('Start with Wi-Fi only: three Wi-Fi names, home on 5 GHz, gadgets on 2.4 GHz, and guests. No new hardware.', 'split', {
        focus: ['wifi', 'iotPlate', 'guestPlate'],
        labels: [['router', 'three Wi-Fi names'], ['homePlate', 'home Wi-Fi'], ['iotPlate', 'gadget Wi-Fi'], ['guestPlate', 'guest Wi-Fi']],
        guest: true,
      }),
      beat('Switch on the 5 GHz radio for the home Wi-Fi, so phones and laptops get the fast band and gadgets keep 2.4 GHz.', 'home', {
        focus: ['wifi', 'homePlate'],
        labels: [['router', '5 GHz for home'], ['phone', 'phone'], ['laptop', 'laptop']],
        guest: true,
      }),
      beat('Then tell the cluster about the new streets: some sites let in only listed streets, and so does the voice rule.', 'chips', {
        focus: ['chip20', 'chip33'],
        labels: [['chip20', 'add the new streets'], ['chip33', 'voice speaker rule']],
        guest: true,
      }),
      beat('Casting and Home Assistant’s device finding stop at the edge of each street. A small router add-on can relay them.', 'iot', {
        focus: ['tv'],
        labels: [['tv', 'casting needs the relay'], ['phone', 'phone']],
        flows: [[['phone', 'router', 'tv'], 'ok']],
        guest: true,
      }),
      beat('The rack switch cannot keep streets apart on its cables. Splitting wired devices later needs a managed switch.', 'lab', {
        focus: ['switch'],
        labels: [['switch', 'unmanaged switch'], ['uplink', 'one cable, many streets later']],
        guest: true,
      }),
      check('On the guest Wi-Fi, a phone loads a website but not 192.168.20.1. If both hold, the split works.', 'guest', {
        focus: ['guestphone'],
        labels: [['guestphone', 'website yes, router no']],
        flows: [[['guestphone', 'router', 'internet'], 'ok'], [['guestphone', 'router'], 'no']],
        guest: true,
      }),
    ],
  },
  {
    id: 'monitoring',
    title: 'Watching the network',
    goal: 'What is recorded today, the gaps, and the alerts worth having.',
    beats: [
      beat('Monitoring means recording how things behave over time, so you notice problems and can look back at them.', 'watch', {
        focus: ['dash'],
        labels: [['dash', 'graphs over time']],
        layers: ['dash'],
      }),
      beat('The cluster already watches itself: Prometheus at .35 collects numbers, and Grafana draws them as graphs.', 'watch', {
        focus: ['chip35', 'dash'],
        labels: [['chip35', 'Prometheus .35'], ['dash', 'Grafana']],
        layers: ['dash'],
        flows: [[['node0', 'switch', 'chip35'], 'ok'], [['node2', 'switch', 'chip35'], 'ok']],
      }),
      beat('The router counts traffic, load and temperature, but keeps them in memory only and nothing draws them as graphs.', 'router', {
        focus: ['router'],
        labels: [['router', 'counts, but no graphs']],
      }),
      beat('Quick win: add luci-app-statistics and the router draws those graphs itself, under Statistics. No cluster needed.', 'router', {
        focus: ['router'],
        labels: [['router', 'Statistics, Graphs']],
      }),
      beat('Its log, a diary of events, should reach node-0. The log file there was last written on 27 April.', 'rack', {
        focus: ['node0'],
        labels: [['node0', 'router log stopped 27 Apr'], ['router', 'sends its log']],
        flows: [[['router', 'switch', 'node0'], 'no']],
      }),
      beat('Add a small exporter to the router and Prometheus can graph its traffic, Wi-Fi devices and port speeds too.', 'watch', {
        focus: ['router', 'chip35'],
        labels: [['router', 'exporter'], ['chip35', 'collects every 30 s']],
        flows: [[['router', 'switch', 'chip35'], 'ok']],
      }),
      beat('Then alerts can tell you when the LAN cable drops to 100 Mb/s, the internet goes down or the router runs hot.', 'watch', {
        focus: ['dash', 'uplink'],
        labels: [['dash', 'alert'], ['uplink', 'speed dropped']],
        layers: ['dash'],
      }),
      beat('Send the router’s log to Loki in the cluster and you can search it, and hear when an unknown device joins.', 'watch', {
        focus: ['node1'],
        labels: [['node1', 'Loki keeps the log'], ['esp', 'new device']],
        flows: [[['router', 'switch', 'node1'], 'ok']],
      }),
    ],
  },
  {
    id: 'more',
    title: 'More you could do',
    goal: 'Private name lookups, ad blocking, smooth calls, tighter Tailscale, and what to do first.',
    beats: [
      beat('Name lookups go from the router to 1.1.1.1 and 8.8.8.8 unencrypted, so your provider can read the names.', 'wan', {
        focus: ['router', 'internet'],
        labels: [['router', 'asks in plain text'], ['internet', '1.1.1.1 and 8.8.8.8']],
        flows: [[['router', 'internet', 'router'], 'ok']],
      }),
      beat('A router add-on can encrypt them. Your provider still sees which addresses you connect to, but not the lookups.', 'wan', {
        focus: ['router'],
        labels: [['router', 'encrypted lookups']],
        flows: [[['router', 'internet', 'router'], 'ok']],
      }),
      beat('The same phone book can refuse the names of ad and tracker servers, which blocks many ads on every device.', 'devices', {
        focus: ['router', 'tv', 'phone'],
        labels: [['router', 'refuses ad names'], ['tv', 'fewer ads on the TV']],
        flows: [[['tv', 'router'], 'no']],
      }),
      beat('Big downloads can fill the line and make calls stutter. Smart queueing, called SQM, keeps a share free for calls.', 'wan', {
        focus: ['router', 'chip30'],
        labels: [['router', 'SQM'], ['chip30', 'torrents']],
        flows: [[['internet', 'router', 'switch', 'chip30'], 'ok'], [['internet', 'router', 'laptop'], 'ok']],
      }),
      beat('Tailscale can have rules too, so a lost phone could reach the websites but not the PiKVM or the cluster computers.', 'tailnet', {
        focus: ['tailnet'],
        labels: [['tailnet', 'Tailscale rules'], ['pikvm', 'refused']],
        layers: ['tailnet'],
        flows: [[['awayphone', 'tailnet', 'router', 'switch', 'chip20'], 'ok'], [['awayphone', 'tailnet'], 'no']],
      }),
      beat('Back up the router under System, Backup. Attended Sysupgrade, already installed, updates it and keeps settings.', 'router', {
        focus: ['router'],
        labels: [['router', 'System, Backup']],
      }),
      beat('In order: replace the LAN cable, add gadget and guest Wi-Fi, graph the router, then add Tailscale rules.', 'tailnet', {
        focus: ['uplink', 'wifi', 'chip35', 'tailnet'],
        labels: [['uplink', '1 new cable'], ['router', '2 gadget and guest Wi-Fi'], ['chip35', '3 router graphs'], ['tailnet', '4 Tailscale rules']],
        layers: ['tailnet'],
      }),
    ],
  },
];

// The Words panel: every term the captions use, in the order they first appear.
export const WORDS = [
  ['Network', 'Devices connected so they can send each other messages.'],
  ['Packet', 'A small piece of a message. Big messages travel as many packets.'],
  ['Address (IP address)', 'Four numbers from 0 to 255, such as 192.168.20.146. Packets are delivered by it.'],
  ['Router', 'The box between your home and the internet. Yours is an OpenWrt One at 192.168.20.1.'],
  ['DHCP', 'How the router lends addresses: a device asks, the router lends a free one for a while.'],
  ['DNS', 'The phone book that turns names such as booklore.soyspray.vip into addresses.'],
  ['Firewall', 'Rules that decide which packets may pass. Yours are in the router and in the cluster.'],
  ['/24', 'Says the first three numbers are fixed and the last one varies: 256 addresses.'],
  ['WAN and LAN', 'WAN is the outside world, the internet. LAN is your home side.'],
  ['Public and private address', 'The internet sees one public address for your home. 192.168 addresses are private and work only inside.'],
  ['NAT', 'The router sends everyone’s traffic out under its one public address and passes replies back.'],
  ['Port', 'A numbered door on an address. Websites use 443; your torrent client uses 49160.'],
  ['VLAN', 'A label on packets that keeps separate networks apart on one cable.'],
  ['Switch', 'A box that joins network cables together. Yours in the rack has 8 ports.'],
  ['Mb/s', 'Megabits per second, the speed of a link. 1000 Mb/s is about 120 megabytes a second.'],
  ['2.4 GHz and 5 GHz', 'The two Wi-Fi radios. 2.4 GHz reaches further; 5 GHz is much faster at short range.'],
  ['PiKVM', 'A remote screen and keyboard for a rack computer, reachable over the network.'],
  ['Cluster', 'Your three computers, node-0 to node-2, running apps together with Kubernetes.'],
  ['MetalLB', 'Gives cluster apps their own addresses on your street, from .20 to .38.'],
  ['Front door (ingress)', 'The app at .20 that reads each website name and passes the request to the right app.'],
  ['Pod', 'A box an app runs in inside the cluster. Each has a hidden 10.233 address.'],
  ['Service', 'One address that stays the same for a group of pods that come and go.'],
  ['Calico', 'Carries traffic between pods on different cluster computers, and applies the cluster’s firewall rules.'],
  ['Tailscale', 'Private tunnels between your own devices, wherever they are. Addresses start 100.'],
  ['Zone', 'A group of connections the router treats alike: home, internet or Tailscale.'],
  ['Network policy', 'A firewall rule inside the cluster that says which pods may talk to which.'],
  ['Subnet', 'One street of addresses, such as 192.168.20.0/24. Devices on it reach each other directly.'],
  ['mDNS', 'How devices announce themselves to others on the same street, for casting and discovery.'],
  ['IoT', 'Internet of things: smart gadgets such as the bulb, vacuum and sensors.'],
  ['Managed switch', 'A switch that understands VLANs, so one cable can carry several streets.'],
  ['Monitoring', 'Recording numbers and events over time so problems show up and can be looked back at.'],
  ['Prometheus and Grafana', 'Prometheus collects numbers from the cluster about every 30 seconds; Grafana draws them as graphs.'],
  ['Exporter', 'A small program that publishes a device’s numbers so Prometheus can collect them.'],
  ['Log and Loki', 'A log is a device’s diary of events. Loki stores logs in the cluster so you can search them.'],
  ['SQM', 'Smart queue management: the router paces traffic so one big download cannot crowd out calls.'],
];

/** Seconds a caption stays on screen: 14 characters a second plus a pause (longer for Try it), at least 5 s. */
export const beatSeconds = (b) => Math.max(5, Math.round((b.text.length / 14 + (b.check ? 3 : 1.6)) * 10) / 10);

/** Absolute times for chapters and beats. */
export function buildTimeline(chapters = CHAPTERS) {
  let t = 0;
  let n = 0;
  const out = chapters.map((c, ci) => {
    const start = t;
    const beats = c.beats.map((b, bi) => {
      const bs = t;
      t += beatSeconds(b);
      return { ...b, start: bs, end: t, index: bi, n: n++, layers: [...(c.layers || []), ...(b.layers || [])], split: !!c.split, chapter: ci, chips: !c.noChips };
    });
    return { ...c, index: ci, start, end: t, beats };
  });
  return { chapters: out, duration: t };
}
