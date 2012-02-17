function [lld, modls, testdat] = gicgmm(mtype, cfix, ctarg);
%defaults are 'full', 'eig', 'sing'

load('rawsingletdata.mat')
load('rawdoubletdata.mat')
% imports rawwaves, an array of singlet-inducing stumuli
% and stimsamps, a cell array arrays of doublet-inducing stimuli

lld = [];
modls = [];
testdat = [];

singmod = buildModel(rawwaves, mtype);

for ind=[1:7]
	isi = ind + 1;
	n = round(size(stimsamps{ind}, 1)*.9);
	dat = stimsamps{ind}(1:n, :);
	tdat = stimsamps{ind}(n+1:end,:);
	length = size(dat, 2);
	dmod = buildModel(dat, mtype);
    ndx=10:9+length;
	smod1.m = singmod.m(ndx);
	smod1.c = singmod.c(ndx,ndx);
	smod2.m = singmod.m(ndx-isi);
	smod2.c = singmod.c(ndx-isi, ndx-isi);
	if strcmp(ctarg, 'sing')
		smod = addMod(smod1, smod2, smod1, cfix);
	else
		smod = addMod(smod1, smod2, dmod, cfix);
	end
	dl = evalGaus(tdat, dmod.m, dmod.c);
	sl = evalGaus(tdat, smod.m, smod.c);
	lld{ind} = {dl,  sl}; %mean(dl - sl);
	modls{ind}=[];
	modls{ind}.d = dmod;
	modls{ind}.s = smod;
	testdat{ind} = tdat;
end

function mod = buildModel(dat, mtype)

mod.m = mean(dat);
mod.c = cov(dat);
if mtype == 'diag'
	mod.c = mod.c .* eye(size(mod.c));
end

function mod = addMod(sm1, sm2, dm, cfix)

mod.m = sm1.m + sm2.m;
mod.c = sm1.c + sm2.c;
if strcmp(cfix, 'det')
	p = 1.0./size(mod.c, 1);
	mod.c = mod.c./(det(mod.c).^p);
	mod.c = mod.c.*(det(dm.c).^p);
elseif strcmp(cfix, 'eig')
	[junk,eb1]=eig(squeeze(mod.c));
	[junk,eb2]=eig(squeeze(dm.c));
	rv=regress(diag(eb2), diag(eb1));
	mod.c=mod.c*rv;
end
