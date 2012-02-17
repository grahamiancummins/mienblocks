import wave, sys, os, getopt


def newSR(fn, nn, sr=44100):
	wr = wave.open(fn) 
	ww = wave.open(nn, 'w')
	pars = wr.getparams()
	#tuple (nchannels, sampwidth, framerate, nframes, comptype, campname)
	pars = list(pars) #tuples are immutable
	pars[2] = sr  #change the framerate 
	ww.setparams(tuple(pars))
	ww.writeframesraw(wr.readframes(wr.getnframes()))


def playWithSR(fn, sr):
	try:
		import ossaudiodev
		wr = wave.open(fn)
		#it worked, so this is Linux or BSD
		ad = ossaudiodev.open('w')
		ad.channels(wr.getnchannels())
		ad.speed(sr)
		if wr.getsampwidth == 2:
			ad.setfmt(ossaudiodev.AFMT_S16_LE)
		else:
			ad.setfmt(ossaudiodev.AFMT_U8)
		ad.writeall(wr.readframes(wr.getnframes()))
	except ImportError:
		try:
			import winsound
			# I guess we're on windows
		except ImportError:
			import Carbon.Snd
			# No, I'm not going to try sunaudiodev, al, or SDL. If this doesn't work I quit
			# If it does work, we're on Mac

usage = '''
python wavtest.py [-w FNAME] [-f SAMPRATE] filename.wav

Convert or play the wave file in filename.wav. By default, this plays the file
as though it had a declared framerate of 44100 Hz. 

If -w FNAME is specified, the file is not played. Instead a copy with the new
declared sample rate is saved to the new file FNAME

If -f SAMPRATE is specified, then SAMPRATE is used instead of 44100Hz as the
new declared sampling rate.

'''

if __name__=='__main__':
	try:
		opts, args = getopt.gnu_getopt(sys.argv[1:], 'f:w:')
		opts = dict(opts)
		if len(args)!=1:
			raise StandardError()
	except:
		print(usage)
		sys.exit()
	if '-f' in opts:
		fs = float(opts['-f'])
	else:
		fs = 44100
	if '-w' in opts:
		newSR(args[0], opts['-w'], fs)
	else:
		playWithSR(args[0], fs)
	
