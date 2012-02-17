 function getHairTF(fname)
% getHairTF(fname)
% This is an MIEN compliant function wrapper for Bree Cummins's stokeslet model of cercal hair motion
% (http://armitage.cns.montana.edu/svn/bree/main/noinversewithcercusdiffdisc/main.m)
% It expects fname to name a file containing a MIEN data element with the following fields:
% data  = vector of frequencies to test
% R  = value of the model constant "R" (viscous resistance) to test 
% S  = value of the model contsant "S" (spring constant) to test
% L  = length of the hair to model
% D  = diameter of the cercus to model
% P  = resting hair position
% The wrapper saves the tf. This is an Nx3 array.
%	N is the length of data data. Each row contains freq, gain, phase, thus tf(:,1) is the same as 
%	freqs, and the other two columns are the gain and phase of a transfer function measured at these
%	frequencies

MPATH = '/Users/gic/bree/noinversewithcercusdiffdisc';
path(MPATH, path);
load(fname);
freqs = data.data;
nfreqs = size(freqs,1);
tf = zeros(nfreqs, 3);
for i = [1:nfreqs]
	f = freqs(i);
	[a, w, s] = main(data.L, 0, 0, 0, f, .001, data.D, data.P, [], [], [], [], [], [], data.R, data.S);
	tf(i, 1)=f;
	tf(i, 2)=abs(a)*1000;
	tf(i, 3)=angle(a);
end
data.data = tf;
save(fname, 'data')





