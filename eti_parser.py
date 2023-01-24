#!/usr/bin/env python3

import os
from pprint import pprint

import curses

screen = curses.initscr()


eti_file = "20150825_14h02_SWR_RP.eti"

# stat = os.stat(eti_file)
# print(stat)

sync0 = (0x07, 0x3A, 0xB6)
sync1 = (0xF8, 0xC5, 0x49)

data = []
with open(eti_file, "rb") as eti:
    data = [i for i in eti.read()]

subchannel = {}
services = {}
ensemble = {"services":services, "label":"", "id":0}

idx = 0
while (idx+2) < len(data):

    pttrn = (data[idx], data[idx+1], data[idx+2])
    sync = False
    parse_fig = False
    idx += 1

    if pttrn == sync0:
        # print(">>> sync0")
        sync = True

    if pttrn == sync1:
        # print(">>> sync1")
        sync = True

    if sync:
        sync = False
        idx += 0x3E
        parse_fig = True
        
    if parse_fig:
        parse_fig = False

        for fib_idx in range(3):
            fib = data[idx:idx+32]
            # print(f"[{fib_idx}]", [hex(i) for i in fib])
            idx += 32

            i = 0
            while (i < 29):
                
                fig_header = fib[i]
                i += 1

                if fig_header == 0xFF:
                    break

                type = (fig_header >> 5) & 0x07
                length = fig_header & 0x1F
                
                if type == 0:
                    fig_data_header = fib[i]
                    i += 1

                    cn = (fig_data_header >> 7) & 0x01
                    oe = (fig_data_header >> 6) & 0x01
                    pd = (fig_data_header >> 5) & 0x01
                    ext = fig_data_header & 0x1F

                    # print(f"[{fib_idx}] FICDecoder: received FIG {type}/{ext} with {length} field bytes")

                    payloadLen = length-1 if length > 0 else length
                    payload = fib[i:(i+payloadLen)]

                    if ext == 0x00:
                        ensid = (payload[0] << 8) | payload[1]
                        changeFlag = payload[2] & 0xC0
                        alFlag = payload[2] & 0x20
                        cifCount = ((payload[2] << 8) | payload[3]) & 0x1FFF
                        occurance = 0 # payload[4]
                        # print(f"eid {hex(ensid)} changeFlag {changeFlag} alFlag {alFlag} cifCount {cifCount} occurance {occurance}")
                        
                        ensemble[f"id"] = hex(ensid)

                    if ext == 0x01:
                        j = 0
                        while j < len(payload)-1:
                            subchId = payload[j+0] >> 2
                            start = ((payload[j+0] << 8) | payload[j+1]) & 0x3FF
                            longForm = (payload[j+2]>>7)
                            # print(f"subchId {subchId} start {start} longForm {longForm}", end=" ")
                            if longForm:
                                option = (payload[j+2] & 0x70) >> 4
                                protectionLevel = (payload[j+2] & 0x0C) >> 2
                                subchSize = ((payload[j+2] << 8) | payload[j+3]) & 0x3FF
                                # print("option {option} protectionLevel {protectionLevel} subchSize {subchSize}")

                                subchannel[f"{subchId}"] = {"start": start, "size": subchSize}

                                j += 4
                            else:
                                tableSwitch = (payload[j+2] & 0x40) >> 4
                                tableIndex = payload[j+2] & 0x3F
                                j += 2

                    elif ext == 0x02:
                        j = 0
                        while j < len(payload)-1:
                            if pd == 0:
                                sid = (payload[j+0] << 8) | payload[j+1] 
                                j += 2
                            else:
                                sid = (payload[j+0] << 24) | (payload[j+1] << 16) | (payload[j+2] << 8) | payload[j+3]
                                j += 4
                            caid = (payload[j+0] & 0x70) >> 4
                            nrcomp = payload[j+0] & 0x0F
                            j += 1
                            for k in range(nrcomp):
                                tmid = payload[j+0] >> 6
                                if tmid == 0 or tmid == 1:
                                    ascty = payload[j+0] & 0x3F
                                    subchId = payload[j+1] >> 2
                                    ps = (payload[j+1] & 0x02) >> 1
                                    caflag = payload[j+1] & 1
                                    # print(f"sid {hex(sid)} caid {caid} nrcomp {nrcomp} tmid {tmid} ascty {ascty} ps {ps} caflag {caflag} subchId {subchId}")

                                    if not f"{hex(sid)}" in services:
                                        services[f"{hex(sid)}"] = {}

                                    services[f"{hex(sid)}"]["subchId"] = f"{subchId}"

                                j += 2


                                
                    
                    i += length-1 if length > 0 else length
                
                elif type == 1:
                    fig_data_header = fib[i]
                    i += 1

                    charset = fig_data_header >> 4
                    ext = fig_data_header & 0x7
                    
                    # print(f"[{fib_idx}] FICDecoder: received FIG {type}/{ext} with {length} field bytes")

                    payloadLen = length-1 if length > 0 else length
                    payload = fib[i:(i+payloadLen)]

                    if ext < 2:
                        label = payload[2:18]
                        label = bytes(label).decode()
                        charField = (payload[18] << 8) | payload[19]

                        if ext == 0:
                            ensid = (payload[0] << 8) | payload[1]
                            # print(f"ensid {hex(ensid)}", end=" ")
                            ensemble["label"] = label
                        
                        elif ext == 1:
                            sid = (payload[0] << 8) | payload[1]
                            # print(f"sid {hex(sid)}", end=" ")
                            
                            if not f"{hex(sid)}" in services:
                                services[f"{hex(sid)}"] = {}

                            services[f"{hex(sid)}"]["label"] = label

                    # print(f"label '{label}' charField {hex(charField)}")



                    i += length-1 if length > 0 else length

                elif type == 2:
                    fig_data_header = fib[i]
                    i += 1

                    ext = fig_data_header & 0x7

                    # print(f"[{fib_idx}] FICDecoder: received FIG {type}/{ext} with {length} field bytes")
                    i += length-1 if length > 0 else length

                else:
                    # print(f">>> error [{fib_idx}] FICDecoder: received FIG {type}/{ext} with {length} field bytes")
                    pass
        
            str_val = f"EnsId : {ensemble['id']}\n"
            str_val += f"EnsLabel : {ensemble['label']}\n"
            for service in ensemble["services"]:
                str_val += f"\tServiceId : {service}\n"
                subchId = ensemble['services'][service]['subchId']
                str_val += f"\t\tSubchannel Id : {subchId}\n"
                if subchId in subchannel:
                    str_val += f"\t\tSubchannel Start : {subchannel[subchId]['start']}\n"
                    str_val += f"\t\tSubchannel Size : {subchannel[subchId]['size']}\n"
                if "label" in ensemble['services'][service]:
                    str_val += f"\t\tLabel : {ensemble['services'][service]['label']}\n"
        
        # print(str_val)
        # screen.clear()
        screen.addstr(0, 0, str(str_val))
        screen.refresh()
        curses.napms(100)

# Changes go in to the screen buffer and only get
# displayed after calling `refresh()` to update

curses.endwin()