import sys
import time
import numpy as np

from subprocess import Popen
from subprocess import PIPE


class Tshark():
    def __init__(self):
        pass

    def translateCSI(self, ifp, ofp, bw=20):
        '''
        extract csi from pcap file according to Nexmon hack
        '''
        FFTlength = 64
        if bw is 40:
            FFTlength = 128
        elif bw is 80:
            FFTlength = 256
        cmd = [
            '-r{0}'.format(ifp),
            '-Tfields',
            '-Eseparator=,',
            '-eframe.time_epoch',
            '-eframe.time_relative',
            '-ewlan.ta',
            '-eframe.len',
            '-edata.data'
        ]
        p = Popen(['tshark'] + cmd, stdout=PIPE)
        try:
            with open(ofp, 'w') as f:
                f.write("#txMAC,time,time_rel")
                for i in range(1, FFTlength + 1):
                    f.write(",sub_{0}_amp,sub_{0}_phase".format(i))
                f.write("\n")
                for line in p.stdout:
                    try:
                        t, t_rel, txMAC, frameLen, data = line.decode().rstrip().split(',')
                    except BaseException as e:
                        print(line)
                        continue
                    if not frameLen == '1076':
                        continue
                    t = float(t)
                    t_rel = float(t_rel)
                    data = data.split(':')
                    if len(data) == 1058:
                        ta = ':'.join(data[32:38])
                        csi_data = data[42:]
                    else:
                        ta = ':'.join(data[8:14])
                        csi_data = data[18:]
                    csi_val = 1j * np.zeros(256)
                    for i in range(0, len(csi_data), 4):
                        real_p = int(
                            "{0}{1}"
                            .format(csi_data[i+3], csi_data[i+2]),
                            16
                        )
                        if real_p > 0x7FFF:
                            real_p -= 0x10000
                        imag_p = int(
                            "{0}{1}"
                            .format(csi_data[i+1], csi_data[i+0]),
                            16
                        )
                        if imag_p > 0x7FFF:
                            imag_p -= 0x10000
                        csi_val[i / 4] = np.complex(real_p, imag_p)
                    if FFTlength < 256:
                        cmplx_bw = np.fft.fftshift(csi_val[1:(FFTlength+1)])
                    else:
                        cmplx_bw = np.fft.fftshift(csi_val[:-1])
                    # set 0 to null carriers
                    if bw is 20:
                        cmplx_bw[:4] = 0
                        cmplx_bw[32] = 0
                        cmplx_bw[61:64] = 0
                    elif bw is 40:
                        cmplx_bw[:6] = 0
                        cmplx_bw[63:66] = 0
                        cmplx_bw[123:128] = 0
                    elif bw is 80:
                        cmplx_bw[:6] = 0
                        cmplx_bw[127:130] = 0
                        cmplx_bw[251:256] = 0
                    f.write("{0},{1:.4f},{2:.4f}".format(ta, t, t_rel))
                    for each in zip(np.abs(cmplx_bw), np.angle(cmplx_bw)):
                        f.write(",{0:.6f},{1:.4f}".format(each[0], each[1]))
                    f.write("\n")
        except KeyboardInterrupt:
            p.kill()
        except Exception:
            raise

    def translatePcap(self, ifp, ofp):
        '''
        translate pcap data into desired format via tshark
        '''
        cmd = [
            '-r{0}'.format(ifp),
            '-Tfields',
            '-Eseparator=,',
            '-ewlan.ta',
            '-eframe.time_epoch',
            '-eframe.time_relative',
            '-ewlan_radio.signal_dbm',
            '-ewlan_radio.noise_dbm',
            '-eframe.len',
            '-eradiotap.channel.freq',
            '-ewlan.fc.type_subtype',
            '-ewlan.frag'
        ]
        p = Popen(['tshark'] + cmd, stdout=PIPE)
        try:
            with open(ofp, 'w') as f:
                f.write("#txMAC,time,time_rel,RSS,noise,frameLen,channelFreq,type,fragNum\n")
                for line in p.stdout:
                    tmp = line.decode()
                    if tmp.split(",")[0]:
                        f.write(tmp)
        except KeyboardInterrupt:
            p.kill()
        except Exception:
            raise


def test(args):
    if args.outf is None:
        print("Must specify output filepath")
        return

    tshark = Tshark()

    if args.rss:
        tshark.translatePcap(args.rss, args.outf)

    elif args.csi:
        tshark.translateCSI(args.csi, args.outf)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='tshark test'
    )

    parser.add_argument(
        '-rss', '--rss',
        dest='rss',
        default=None,
        help='Specify RSS pcap file path'
    )

    parser.add_argument(
        '-csi', '--csi',
        dest='csi',
        default=None,
        help='Specify CSI pcap file path'
    )

    parser.add_argument(
        '-o', '--outf',
        dest='outf',
        default=None,
        help='Specify output filepath'
    )

    args, __ = parser.parse_known_args()

    test(args)

