PROGRAM mapseek
	IMPLICIT NONE
	INTEGER :: GRID,LAYERS,RES, NTRANS, maxiter
	REAL kappa
	REAL, DIMENSION(100,100) :: inp, outp	
	INTEGER, DIMENSION(72,2) :: transmat
	COMMON transmat, GRID, RES, NTRANS, LAYERS
	real , DIMENSION(3,100,100) :: forward
	real , DIMENSION(3,100,100) :: reverse
	real , DIMENSION(3,72) :: weights
	real , DIMENSION(72) :: q
	real , DIMENSION(3,72,100,100) :: stacks
	real , DIMENSION(72,100,100) :: ostack
	real , DIMENSION(72,100,100) :: temp
	integer iter, atlayer
	logical done
	GRID=100
	RES=5
	LAYERS=3
	NTRANS=360/RES
	kappa=.5
	maxiter=200
	CALL mktransmat
	!comment
	inp=0
	outp=0
	stacks=0
	weights=1.0
	forward=0
	done=.false.
	inp(40, 40)=1.0;
	outp(70, 40)=1
	WRITE (*,*) "Starting ..."
	stacks(1,:,:,:)=transform(inp, 1)	
	ostack=transform(outp, -1)
	mainloop:do iter=1,maxiter,1
		write (*,*) iter
		forward(1,:,:)=addstack(stacks(1,:,:,:), weights(1,:))
		do atlayer=2,3,1
			stacks(atlayer,:,:,:)=transform(forward(atlayer-1,:,:), 1)
			forward(atlayer,:,:)=addstack(stacks(atlayer,:,:,:), weights(atlayer, :))
		end do
		reverse(3,:,:)=addstack(ostack, weights(3,:))
		do atlayer=2,1,-1
			temp=transform(reverse(atlayer+1,:,:), -1)
			reverse(atlayer,:,:)=addstack(temp, weights(atlayer, :))
		end do		
		done=.true.
		do atlayer=1,3,1
			if (atlayer .eq. 3) then
				q=check(stacks(atlayer, :, :, :), outp)
			else
				q=check(stacks(atlayer, :, :, :), reverse(atlayer+1, :,:))
			end if
			call adjweights(q, weights(atlayer,:), kappa)
			if (.not. all( weights(atlayer,:)<=0.05 .or.  weights(atlayer,:)>=0.95)) then 
				done=.false. 
			end if	
		end do
		if (done) exit mainloop	
	end do mainloop
	WRITE (*,*) "done"
	do atlayer=1,3,1
		write(*,*) atlayer, "->"
		do iter=1,72,1
			if (weights(atlayer, iter) .ne. 0) then 
				write(*,*) iter
				write(*,*) transmat(iter, :)
			end if	
		end do 
	end do	
	contains
		function addstack(stack, weights)
			real, DIMENSION(72,100,100) :: stack
			real, DIMENSION(72) :: weights
			real, DIMENSION(100,100) :: addstack
			integer i
			addstack=0
			do i=1,72,1
				addstack=addstack+stack(i,:,:)*weights(i)
			end do
			!addstack=addstack/maxval(addstack)
		end function addstack			
		subroutine adjweights(q, weights, kappa)
			real, DIMENSION(72) :: q, weights
			real kappa, mv, nw
			integer i
			do i=1,72,1 
				nw=weights(i)-kappa*(1-q(i))
				if (nw .gt. 0) then
					weights(i)=nw
				else
					weights(i)=0
				end if
			end do
			mv=maxval(weights)
			if (mv .eq. 0.0) then
				write(*,*) "no mapping"
				return
			end if	
			weights=weights/mv
		end subroutine adjweights
		function check(stack, image)
			real, intent(in), DIMENSION(100,100) :: image
			real, intent(in), DIMENSION(72, 100,100) :: stack
			real, DIMENSION(72) :: check
			integer i
			check=0
			do i=1,72,1
				check(i)=sum(image*stack(i,:,:))
			end do
			check=check/maxval(check)
		end function check
		function transform(in, mode) 
			real, intent(in), DIMENSION(100,100) :: in
			integer :: mode, i, xmin, ymin, ymax, oymin, oymax, xmax, oxmin, oxmax, xs, ys
			real, DIMENSION(72,100,100) :: transform
			transform=0
			do i=1,NTRANS,1
				xs=transmat(i,1)*mode
				ys=transmat(i,2)*mode
				if (xs .GE. 0) then
					xmin=1
					oxmin=xs+1
					xmax=100-xs
					oxmax=100
				else
					xmin=abs(xs)+1
					xmax=100
					oxmin=1
					oxmax=100+xs
				end if 	
				if (ys .GE. 0) then
					ymin=1
					oymin=ys+1
					ymax=100-ys
					oymax=100
				else
					ymin=abs(ys)+1
					ymax=100
					oymin=1
					oymax=100+ys
				end if 			
				transform(i,oxmin:oxmax,oymin:oymax)=in(xmin:xmax,ymin:ymax)
				!write (*,*) i, xs, ys, oxmin, oxmax, oymin, oymax, xmin, xmax, ymin, ymax
				!write (*,*) maxloc(transform(i,:,:))
				
			end do	
		end function transform
		subroutine mktransmat
			integer i;
			real thet, x,y
			real, parameter :: pi=3.1415927, len=30.0
			do i=0,NTRANS-1,1
				thet=pi*i*RES/180.0
				x=len*cos(thet);
				y=len*sin(thet);
				transmat(i+1, 1)=floor(x+.5);
				transmat(i+1, 2)=floor(y+.5);
			end do
		end subroutine mktransmat
END PROGRAM mapseek
