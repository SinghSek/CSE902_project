# 3GPP components quick reference (5G focus)

## Network entities (104)

| Component | Description |
|---|---|
| UE | User Equipment: the subscriber device (ME + USIM). |
| ME | Mobile Equipment: UE hardware, identified by PEI/IMEI. |
| USIM | Universal Subscriber Identity Module: holds SUPI/IMSI, key K, SUCI public key. |
| 5G-RG | 5G Residential Gateway: home gateway acting as a UE over wireline or FWA. |
| N5CW device | Non-5G-capable Wi-Fi device, served via the TWIF. |
| NG-RAN | Next Generation RAN: the 5G radio access network (gNBs, ng-eNBs). |
| gNB | Next Generation NodeB: 5G NR base station. |
| gNB-CU | gNB Central Unit: hosts RRC, SDAP, PDCP; controls DUs. |
| gNB-CU-CP | gNB-CU control plane: RRC and control-plane PDCP. |
| gNB-CU-UP | gNB-CU user plane: SDAP and user-plane PDCP. |
| gNB-DU | gNB Distributed Unit: hosts RLC, MAC, PHY. |
| ng-eNB | LTE base station connected to the 5G Core. |
| en-gNB | NR secondary node in EN-DC (non-standalone 5G). |
| IAB-node | Integrated Access and Backhaul node: relay with wireless NR backhaul. |
| IAB-donor | gNB providing the network connection for IAB-nodes. |
| TRP | Transmission Reception Point: antenna site sending PRS / measuring SRS for positioning. |
| NTN | Non-Terrestrial Network: satellite/HAPS-based NR or IoT access. |
| eNB | Evolved NodeB: LTE base station. |
| UTRAN | Legacy 3G radio access (NodeB/RNC). |
| GERAN | Legacy 2G radio access (BTS/BSC). |
| AMF | Access and Mobility Management Function: registration, mobility, paging, NAS termination. |
| SEAF | Security Anchor Function (in AMF): holds the anchor key after authentication. |
| SMF | Session Management Function: PDU sessions, IP allocation, UPF control. |
| UPF | User Plane Function: forwards and processes user data traffic. |
| PCF | Policy Control Function: QoS, charging, mobility and UE (URSP) policies. |
| UDM | Unified Data Management: subscription data, auth vectors, SUCI de-concealment. |
| ARPF | Authentication credential Repository and Processing Function (in UDM): stores K, makes auth vectors. |
| SIDF | Subscription Identifier De-concealing Function (in UDM): SUCI to SUPI. |
| UDR | Unified Data Repository: database for subscription, policy and exposure data. |
| UDSF | Unstructured Data Storage Function: stores NF context data. |
| AUSF | Authentication Server Function: runs 5G AKA / EAP-AKA' for the home network. |
| NRF | Network Repository Function: NF registration, discovery, access tokens. |
| NSSF | Network Slice Selection Function: picks slices and the serving AMF set. |
| NEF | Network Exposure Function: exposes network events/capabilities to external apps. |
| NWDAF | Network Data Analytics Function: network analytics and ML predictions. |
| AF | Application Function: application interacting with the core (QoS, routing). |
| SCP | Service Communication Proxy: routes signalling between NFs. |
| SEPP | Security Edge Protection Proxy: secures roaming signalling between operators. |
| N3IWF | Non-3GPP InterWorking Function: gateway for untrusted Wi-Fi (IPsec). |
| TNGF | Trusted Non-3GPP Gateway Function: gateway for trusted Wi-Fi. |
| TNAP | Trusted Non-3GPP Access Point: Wi-Fi AP in a trusted access network. |
| TWIF | Trusted WLAN Interworking Function: serves non-5G-capable Wi-Fi devices. |
| W-AGF | Wireline Access Gateway Function: connects fixed broadband to 5GC. |
| NSSAAF | Network Slice-Specific Authentication and Authorization Function: slice auth via external AAA. |
| NSACF | Network Slice Admission Control Function: caps UEs/sessions per slice. |
| CHF | Charging Function: online/offline charging and quotas. |
| SMSF | Short Message Service Function: SMS over NAS. |
| LMF | Location Management Function: 5G positioning server; computes UE location. |
| GMLC | Gateway Mobile Location Centre: entry point for location requests (incl. PSAPs). |
| LRF | Location Retrieval Function: location/routing info for IMS emergency calls. |
| 5G-EIR | Equipment Identity Register: checks IMEI/PEI against blocklists. |
| BSF | Binding Support Function: maps PDU sessions to their PCF. |
| UCMF | UE radio Capability Management Function: stores radio capability IDs. |
| AAnF | AKMA Anchor Function: application keys from 5G authentication. |
| DCCF | Data Collection Coordination Function: coordinates analytics data collection. |
| ADRF | Analytics Data Repository Function: stores analytics data and ML models. |
| MFAF | Messaging Framework Adaptor Function: delivers collected data to consumers. |
| EASDF | Edge Application Server Discovery Function: DNS steering to edge servers. |
| TSCTSF | Time Sensitive Communication and Time Synchronization Function. |
| TSN AF | TSN Application Function: interfaces 5GS with IEEE TSN networks. |
| MB-SMF | Multicast/Broadcast SMF: manages MBS sessions. |
| MB-UPF | Multicast/Broadcast UPF: user plane for MBS traffic. |
| MBSF | Multicast/Broadcast Service Function: MBS service layer. |
| 5G DDNMF | 5G Direct Discovery Name Management Function: ProSe discovery codes. |
| ProSe AS | ProSe Application Server: proximity services. |
| V2X AS | V2X Application Server: vehicle communication services. |
| DN | Data Network: external network (internet, IMS, enterprise) reached via the UPF. |
| CBCF | Cell Broadcast Centre Function: delivers public warnings in 5G. |
| PWS-IWF | PWS InterWorking Function: connects a legacy CBC to 5GC. |
| CBC | Cell Broadcast Centre: delivers public warnings in LTE. |
| CBE | Cell Broadcast Entity: alert originator (e.g. government agency). |
| SMS-SC | SMS Service Centre: stores and forwards SMS. |
| LCS Client | Location Services client: app/entity requesting a UE's location. |
| PSAP | Public Safety Answering Point: emergency call centre. |
| SLP | SUPL Location Platform (OMA): user-plane location server. |
| LI functions | Lawful Interception functions (ADMF, POI, MDF): legal intercept. |
| EAS | Edge Application Server: app instance at the network edge. |
| EES | Edge Enabler Server: edge discovery/registration services. |
| ECS | Edge Configuration Server: provides edge network config to UEs. |
| EEC | Edge Enabler Client: UE-side edge client. |
| MCPTT server | Mission Critical Push-To-Talk server: public safety PTT. |
| MCData server | Mission Critical Data server: MC messaging and file sharing. |
| MCVideo server | Mission Critical Video server. |
| SEAL servers | Service Enabler Architecture Layer: common identity, key, group, location services. |
| MME | Mobility Management Entity: LTE core control node. |
| S-GW | Serving Gateway: LTE user-plane mobility anchor. |
| P-GW | PDN Gateway: LTE gateway to external networks. |
| HSS | Home Subscriber Server: LTE/IMS subscriber database. |
| PCRF | Policy and Charging Rules Function: LTE policy. |
| SCEF | Service Capability Exposure Function: LTE exposure (IoT). |
| E-SMLC | Evolved Serving Mobile Location Centre: LTE positioning server. |
| MSC | Mobile Switching Centre: legacy circuit-switched core (CSFB, SRVCC). |
| P-CSCF | Proxy CSCF: UE's first IMS contact; detects emergency calls. |
| I-CSCF | Interrogating CSCF: home IMS entry point, finds the S-CSCF. |
| S-CSCF | Serving CSCF: IMS registrar and session control. |
| E-CSCF | Emergency CSCF: routes IMS emergency calls to PSAPs. |
| IBCF | Interconnection Border Control Function: IMS border / SBC. |
| BGCF | Breakout Gateway Control Function: routes calls to the PSTN. |
| MGCF | Media Gateway Control Function: IMS to PSTN interworking. |
| MRF | Media Resource Function: conferencing, announcements. |
| MMTel AS | Multimedia Telephony Application Server: IMS telephony services. |
| SCC AS | Service Centralization and Continuity AS: anchors calls for SRVCC. |
| ATCF/ATGW | Access Transfer Control Function / Gateway: speeds up SRVCC. |
| EATF | Emergency Access Transfer Function: SRVCC for emergency calls. |

## Interfaces (79)

| Component | Description |
|---|---|
| Uu | UE to base station radio interface. |
| PC5 | UE to UE sidelink (ProSe, V2X). |
| N1 | UE to AMF: NAS signalling. |
| N2 | RAN to AMF: control plane (NGAP). |
| N3 | RAN to UPF: user plane (GTP-U). |
| N4 | SMF to UPF: user-plane control (PFCP). |
| N6 | UPF to Data Network. |
| N9 | UPF to UPF user plane. |
| N19 | UPF to UPF tunnel for 5G LAN groups. |
| NWu | UE to N3IWF: IPsec tunnel over untrusted Wi-Fi. |
| NWt | UE to TNGF: tunnel over trusted Wi-Fi. |
| Y2 | Untrusted Wi-Fi network to N3IWF. |
| Xn | gNB to gNB: handover, dual connectivity. |
| F1 | gNB-CU to gNB-DU. |
| E1 | gNB-CU-CP to gNB-CU-UP. |
| X2 | eNB to eNB / eNB to en-gNB (LTE, NSA). |
| N5 | PCF to AF: application QoS requests. |
| N7 | SMF to PCF: session policy. |
| N8 | AMF to UDM: subscription data. |
| N10 | SMF to UDM: session subscription data. |
| N11 | AMF to SMF: PDU session control. |
| N12 | AMF to AUSF: authentication. |
| N13 | AUSF to UDM: authentication vectors. |
| N14 | AMF to AMF: UE context transfer. |
| N15 | AMF to PCF: mobility and UE policy. |
| N16 | SMF to SMF: roaming / intermediate SMF. |
| N17 | AMF to 5G-EIR: IMEI check. |
| N18 | NF to UDSF: context storage. |
| N20 | AMF to SMSF: SMS. |
| N21 | SMSF to UDM: SMS subscription. |
| N22 | AMF to NSSF: slice selection. |
| N23 | PCF to NWDAF: analytics for policy. |
| N24 | Visited PCF to home PCF (roaming). |
| N27 | Visited NRF to home NRF (roaming). |
| N28 | PCF to CHF: spending limits. |
| N29 | NEF to SMF. |
| N30 | PCF to NEF. |
| N31 | Visited NSSF to home NSSF (roaming). |
| N33 | NEF to AF: northbound exposure APIs. |
| N34 | NSSF to NWDAF. |
| N35 | UDM to UDR. |
| N36 | PCF to UDR. |
| N37 | NEF to UDR. |
| N40 | SMF to CHF: session charging. |
| N50 | AMF to CBCF: public warnings. |
| N51 | AMF to NEF. |
| N52 | NEF to UDM. |
| N58 | AMF to NSSAAF: slice authentication. |
| N59 | UDM to NSSAAF. |
| N26 | MME to AMF: 5G-LTE interworking. |
| N32 | SEPP to SEPP: secure roaming signalling. |
| NL1 | AMF to LMF: positioning. |
| NL2 | AMF to GMLC: location requests. |
| NL3 | GMLC to GMLC (roaming). |
| NL5 | NEF to GMLC: location exposure. |
| NL6 | UDM to GMLC: serving AMF and privacy lookup. |
| Le | LCS client / PSAP to GMLC (MLP). |
| SLs | MME to E-SMLC: LTE positioning. |
| SLg | MME to GMLC: LTE location. |
| SLh | HSS to GMLC. |
| S1-MME | eNB to MME: control plane. |
| S1-U | eNB to S-GW: user plane. |
| S5/S8 | S-GW to P-GW (S8 when roaming). |
| S6a | MME to HSS: subscription and authentication. |
| S10 | MME to MME. |
| S11 | MME to S-GW. |
| SGi | P-GW to external network. |
| Gx | P-GW to PCRF: policy rules. |
| Rx | AF / P-CSCF to PCRF: QoS requests. |
| SGs | MME to MSC: CS fallback, SMS. |
| Sv | MME to MSC: SRVCC. |
| SBc | MME to CBC: public warnings (LTE). |
| T8 | SCEF to application server API. |
| Gm | UE to P-CSCF: SIP. |
| Mw | CSCF to CSCF: SIP. |
| Cx | CSCF to HSS: IMS registration and authentication. |
| Sh | IMS application server to HSS. |
| ISC | S-CSCF to application server. |
| Ml | E-CSCF to LRF: emergency routing and location. |

## Protocols (48)

| Component | Description |
|---|---|
| 5GMM | 5G NAS Mobility Management: registration, security, mobility. |
| 5GSM | 5G NAS Session Management: PDU sessions. |
| EMM | LTE NAS mobility management. |
| ESM | LTE NAS session management. |
| NR RRC | NR Radio Resource Control: radio connection, mobility, broadcast. |
| LTE RRC | LTE Radio Resource Control. |
| SDAP | Service Data Adaptation Protocol: maps QoS flows to radio bearers. |
| PDCP | Packet Data Convergence Protocol: radio ciphering, integrity, compression. |
| RLC | Radio Link Control: segmentation, retransmission (ARQ). |
| MAC | Medium Access Control: scheduling, HARQ, random access. |
| NR PHY | NR physical layer. |
| BAP | Backhaul Adaptation Protocol: IAB routing. |
| PC5 signalling | Sidelink signalling (PC5-S / PC5-RRC). |
| NGAP | NG Application Protocol: RAN to AMF signalling. |
| XnAP | Xn Application Protocol: gNB to gNB signalling. |
| F1AP | F1 Application Protocol: CU to DU signalling. |
| E1AP | E1 Application Protocol: CU-CP to CU-UP signalling. |
| S1AP | S1 Application Protocol: eNB to MME signalling. |
| X2AP | X2 Application Protocol: eNB to eNB signalling. |
| NRPPa | NR Positioning Protocol A: RAN to LMF positioning. |
| LPPa | LTE Positioning Protocol A: eNB to E-SMLC. |
| LPP | LTE Positioning Protocol: UE to location server (LTE and NR). |
| LCS-AP | LCS Application Protocol: MME to E-SMLC. |
| ELP | EPC LCS Protocol: MME to GMLC. |
| MLP | Mobile Location Protocol (OMA): client / PSAP to GMLC. |
| SUPL | Secure User Plane Location (OMA): IP-based positioning. |
| PFCP | Packet Forwarding Control Protocol: SMF controls the UPF. |
| GTP-U | GTP user plane: tunnels user data. |
| GTPv2-C | GTPv2 control plane: LTE core signalling and N26. |
| HTTP/2 | HTTP/2: transport for 5G core APIs. |
| SBI (JSON/OpenAPI) | 5G core REST/JSON APIs (OpenAPI). |
| SCTP | Stream Control Transmission Protocol: transport for RAN signalling. |
| IP | IPv4/IPv6 with UDP/TCP. |
| TLS | Transport Layer Security: protects core APIs and N32. |
| PRINS | PRotocol for N32 INterconnect Security: application-layer roaming protection. |
| OAuth 2.0 | OAuth 2.0: token-based NF authorization. |
| IPsec | IPsec: IP-layer tunnel security. |
| IKEv2 | Internet Key Exchange v2: sets up IPsec tunnels. |
| EAP | Extensible Authentication Protocol framework. |
| EAP-AKA' | EAP-AKA': EAP-based 5G primary authentication. |
| NEA/NIA | NEA/NIA: 5G ciphering and integrity algorithms. |
| Diameter | Diameter: AAA signalling in LTE and IMS. |
| SIP | Session Initiation Protocol: IMS call/session signalling. |
| SDP | Session Description Protocol: media negotiation. |
| RTP/RTCP | Real-time Transport Protocol: voice/video media. |
| SM-CP/SM-RP | SMS transport protocols (SM-CP/SM-RP). |
| SGsAP | SGs Application Part: MME to MSC. |
| SBc-AP | SBc Application Part: CBC to MME warnings. |

## Procedures (100)

| Component | Description |
|---|---|
| Initial Registration | UE registers with the 5G core (authentication, security, slices). |
| Mobility Registration Update | Re-registration after leaving the tracking area list. |
| Periodic Registration Update | Timer-driven (T3512) registration to confirm reachability. |
| Emergency Registration | Registration for emergency services only. |
| Deregistration | UE- or network-initiated detach. |
| Service Request | Idle UE resumes connection and user plane. |
| Paging | Network locates an idle or inactive UE. |
| AN Release | Releases the RAN connection; UE goes idle. |
| UE Configuration Update | Network updates UE settings (GUTI, NSSAI, etc.). |
| MICO / eDRX / PSM | MICO / eDRX / PSM power-saving modes. |
| Identification | Network requests UE identity (SUCI, IMEI). |
| ME Identity Check | IMEI check against the 5G-EIR. |
| RRC Connection Establishment | Establishes the RRC connection. |
| RRC_INACTIVE / RRC Resume | RRC_INACTIVE state and RRC resume. |
| RRC Reconfiguration | Modifies radio bearers, measurements, handover. |
| RRC Release | Releases or suspends the RRC connection. |
| RRC Re-establishment | Recovers after radio link failure. |
| System Information Broadcast | MIB/SIB broadcast of cell information. |
| Random Access | RACH: initial uplink access. |
| Cell Selection / Reselection | Idle UE chooses which cell to camp on. |
| Measurement Reporting | UE reports radio measurements. |
| UE Capability Transfer | UE reports its radio capabilities. |
| AS Security Mode Command | Activates radio (AS) encryption and integrity. |
| Dual Connectivity (EN-DC / MR-DC) | EN-DC / MR-DC: two base stations at once (incl. NSA). |
| Xn Handover | Handover directly between gNBs. |
| N2 Handover | Handover via the AMF. |
| Conditional Handover | UE executes a pre-configured handover. |
| 5GS-EPS Handover (N26) | 5G to LTE connected handover via N26. |
| 5GS-EPS Idle Mobility / Interworking | 5G to LTE idle-mode mobility. |
| EPS Attach | LTE registration. |
| Tracking Area Update | LTE location update. |
| SRVCC / 5G-SRVCC | Moves an IMS voice call to 2G/3G circuit switched. |
| CS Fallback | LTE UE falls back to 2G/3G for voice. |
| EPS Fallback for Voice | 5G voice call moved to VoLTE. |
| PDU Session Establishment | Sets up a data session. |
| PDU Session Modification | Changes session QoS. |
| PDU Session Release | Ends a data session. |
| SSC Mode / UPF Relocation | SSC modes: changing the session anchor UPF. |
| ULCL / Branching Point | Local traffic breakout (e.g. to edge). |
| QoS Flow Management | 5G QoS model (QoS flows, 5QI). |
| EPS Bearer / PDN Connectivity | LTE default/dedicated bearers. |
| Emergency PDU Session | Data session for IMS emergency calls. |
| AM Policy Association | AMF gets mobility policy from the PCF. |
| SM Policy Association | SMF gets session policy (PCC rules) from the PCF. |
| UE Policy Delivery (URSP) | PCF sends URSP policies to the UE. |
| Policy Authorization (AF session) | Application/IMS requests QoS from the PCF. |
| 5G AKA | 5G AKA authentication. |
| EAP-AKA' Authentication | EAP-AKA' authentication. |
| EAP-TLS Authentication | Certificate-based authentication (private networks). |
| SUCI Concealment | Encrypts the SUPI as SUCI (ECIES). |
| NAS Security Mode Command | Activates NAS encryption and integrity. |
| 5G Key Hierarchy & Derivation | Derivation of 5G keys, incl. at handover. |
| Secondary Authentication | External DN-AAA authentication of a session. |
| NSSAA | Slice-specific authentication. |
| AKMA | Application keys derived from 5G authentication. |
| SoR / UPU Protection | Protected roaming steering and UE parameter updates. |
| SBA Security (mTLS & OAuth 2.0) | Mutual TLS and OAuth 2.0 between core functions. |
| N32 Inter-PLMN Security | Securing roaming signalling between SEPPs. |
| EPS AKA | LTE authentication. |
| False Base Station Detection | Detecting fake base stations from UE reports. |
| Lawful Interception | Legal interception of communications. |
| Network Slice Selection | Choosing slices (NSSAI) for a UE. |
| Network Slice Admission Control | Per-slice admission limits. |
| NF Registration | NF registers with the NRF. |
| NF Discovery | NF finds other NFs via the NRF. |
| 5GC-MT-LR | External request for a UE's location. |
| 5GC-MO-LR | UE requests its own location. |
| 5GC-NI-LR | Network-triggered location for emergency calls. |
| Deferred 5GC-MT-LR | Periodic or event-based location reporting. |
| EPC Location Procedures | LTE location procedures. |
| NG-RAN Positioning Procedure | LMF positions the UE via LPP/NRPPa. |
| Location Privacy | User privacy check for location requests. |
| A-GNSS Positioning | Assisted satellite (GPS/GNSS) positioning. |
| E-CID Positioning | Cell-ID based positioning. |
| DL-TDOA / OTDOA | Downlink time-difference positioning. |
| UL-TDOA | Uplink time-difference positioning. |
| Multi-RTT | Round-trip-time positioning. |
| DL-AoD / UL-AoA | Angle-based positioning. |
| Sensor / WLAN / Bluetooth / TBS / Barometric | Sensor, WLAN, Bluetooth and barometric positioning. |
| Sidelink Positioning | UE to UE ranging/positioning. |
| IMS Emergency Session | IMS emergency call routed to a PSAP. |
| Emergency Services Fallback | Emergency call moved from 5G to LTE. |
| Emergency Number Handling | Emergency number lists and emergency call detection. |
| eCall over IMS | Vehicle emergency call over IMS. |
| Public Warning Delivery | Public warning broadcast (ETWS/CMAS/WEA). |
| IMS Registration | UE registers with IMS. |
| IMS Voice/Video Call Setup | VoNR/VoLTE call setup. |
| P-CSCF Discovery | UE learns the P-CSCF address. |
| SMS over NAS | SMS carried in NAS signalling. |
| Event Exposure / Monitoring | External apps subscribe to network events. |
| AF Traffic Influence | App steers traffic routing (e.g. to edge). |
| NWDAF Analytics | Requesting network analytics. |
| Converged Charging | Usage reporting and quota management. |
| Untrusted Non-3GPP Access Registration | Registration over untrusted Wi-Fi via the N3IWF. |
| Trusted Non-3GPP Access Registration | Registration over trusted Wi-Fi via the TNGF. |
| Edge Application Discovery & Relocation | Finding and relocating edge application servers. |
| 5G ProSe | Direct UE discovery, communication and relay. |
| V2X Communication | Vehicle communication (V2V, V2I). |
| 5G MBS Session | Multicast/broadcast sessions. |
| MCPTT Call | Mission-critical push-to-talk calls. |
