 function matlablistener(datafile, semaphore, mfile, mfiledir)
% launch a MIEN matlabservice listener. See mienblocks.bree.matlabService for details
% semaphores:
% 1 -> process
% 0 -> wait
% -1 -> exit

path(mfiledir, path);

cmd = [mfile, '(''', datafile, ''')']

while 1
	sv = dlmread(semaphore);
	if sv == -1
		break
	elseif sv == 0
		pause(.5)
	elseif sv == 1
		try
			%display('start eval')
			eval(cmd)
			%display('end eval')
			sv = dlmread(semaphore);
			if sv == -1
				break
			end
			dlmwrite(semaphore, 0)
		catch
			display('eval failed')
			dlmwrite(semaphore, 0)
		end
	end
end
display('matlab listener exiting')
try
	delete(semaphore)
	delete(datafile)
catch
	display('file cleanup failed')
end
quit

