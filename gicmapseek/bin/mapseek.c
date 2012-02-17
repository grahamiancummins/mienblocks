//mapssek.c
#include <math.h>

#include <stdio.h>
#include <stdlib.h>
#define GRID 100
#define  LAYERS 3
#define	RES 5.0
#define  NTRANS 72

int transmat[NTRANS][2];

void mktransmat()
{
	int i;
	float thet, len, x, y;
	len=30.0;
	for (i=0;i<NTRANS;i++)
	{
		thet=3.1415927*i*RES/180.0;
		x=len*cos(thet);
		y=len*sin(thet);
		transmat[i][0]=floor(x+.5);
		transmat[i][1]=floor(y+.5);
	}
}

struct mscpars 
{ 
	int maxiter;
	float kappa;
};

float fasum(float *thing, int count)
{
	int i;
	float s=0.0;
	for (i=0;i<count;i++)
	{
		s+=*(thing+i);
	}
	return s;
}

void transform(float in[GRID][GRID], float *out, int scale)
{
	//out is [NTRANS][GRID][GRID]
	int t,i,j,sx,sy;
	for (t=0;t<NTRANS;t++)				
	{	
		sx=scale*transmat[t][0];
		sy=scale*transmat[t][1];
		//printf("%i,%i,%i\n", t, sx, sy);
		
		for (i=0;i<GRID;i++)
		{
			for (j=0;j<GRID;j++)
			{
				if (i-sx>=0 && i-sx<GRID && j-sy>=0 && j-sy<GRID)
				{
					*(out+t*GRID*GRID+i*GRID+j)=in[i-sx][j-sy];
					//if (in[i-sx][j-sy])
					//	{printf("%i %i %i\n", t, i, j);}
				} else {
					*(out+t*GRID*GRID+i*GRID+j)=0.0;
				}
			}
		}
		//printf("%i %.2f\n", t, fasum(out, (t+1)*GRID*GRID));
		
	}
	
}

void addstack(float *in, float *g, float *out)
{
// in is NxGxG, g is N, out is GxG
	int i,j,l;
	float accum, max;
	max=0.9;
	for (i=0;i<GRID;i++)
	{
		for (j=0;j<GRID;j++)
		{
			accum=0.0;
			for (l=0;l<NTRANS;l++)
			{
				accum+=*(in + l*GRID*GRID+i*GRID+j)*(*(g+l));
			}	
			if (accum>max)
				max=accum;
			*(out+i*GRID+j)=accum;
		}
	}	
	for (i=0;i<GRID;i++)
	{
		for (j=0;j<GRID;j++)
		{
			*(out+i*GRID+j)=*(out+i*GRID+j)/max;
		}	
	}
}

float dot(float *a, float *b)
{
	int i,j;
	float accum=0;
	for (i=0;i<GRID;i++)
	{
		for (j=0;j<GRID;j++)
		{
			accum+=*(a+i*GRID+j)*(*(b+i*GRID+j));
		}
	}	
	return accum;
}


void checkmatch(float *stack, float *targ, float q[NTRANS])
{
	int l, i, j;
	float max;
	max=0.0;
	//printf("check\n");
	for (l=0;l<NTRANS;l++)
	{
		q[l]=dot(stack+l*GRID*GRID, targ);
		/*printf("%.2f %.2f %.2f  | ", asum(stack[l]), asum(targ), q[l]);
		if (q[l]<0) {
			max=0;
			for (i=0;i<GRID;i++)
			{
				for (j=0; j<GRID;j++)
				{
				max+=stack[l][i][j]*targ[i][j];
				}
				if (max<0)
				{
					printf("%i %i\n", i, j);
				}	
			}
			printf("%.2f  %.2f\n", q[l], max);
			exit(1);
		}
		*/
		if (q[l]>max)
			max=q[l];
	}
	//printf("\n");
	if (max==0)
		{
		printf("mapping does not exist\n");
		//printf("%.2f %.2f\n", asum(targ), ssum(stack));
		
		exit(1);
		}
	for (l=0;l<NTRANS;l++)
	{
		q[l]=q[l]/max;
	}	
}

int adjweights(float q[NTRANS], float *weights, float k)
{
	int l;
	float max, pen, nw;
	max=0.0;
	int notconv=0;
	for (l=0;l<NTRANS;l++)
	{
		pen=k*(1-q[l]);
		nw=weights[l]-pen;
		if (nw<0)
			nw=0.0;
		else if (nw>max)
			max=nw;
		weights[l]=nw;
	}
	if (max==0)
		{
		printf("mapping does not exist\n");
		exit(1);
		}
	//printf("\n\n");
	for (l=0;l<NTRANS;l++)
	{
		
		weights[l]=weights[l]/max;
		if (weights[l]<.95 && weights[l]>.05)
			notconv=1;
		//printf(" %.2f ", weights[l]);
	}	
	//printf("\n\n");
	return notconv;
}


static void mapseek(float in[GRID][GRID], float out[GRID][GRID], struct mscpars *par) 
{
	//float forward[LAYERS][GRID][GRID];
	//float reverse[LAYERS][GRID][GRID];
	//float weights[LAYERS][NTRANS];
	float q[NTRANS];
	//float stacks[LAYERS][NTRANS][GRID][GRID];
	//float ostack[NTRANS][GRID][GRID];
	//float temp[NTRANS][GRID][GRID];
	float *forward, *reverse, *weights, *stacks, *ostack, *temp;
	float test;
	int iter, atlayer;
	int done=0;
	int i,j, cf;
	int al=LAYERS*GRID*GRID;
	forward=calloc(al, sizeof(float));
	reverse=calloc(al, sizeof(float));
	weights=calloc(NTRANS*LAYERS, sizeof(float));
	stacks=calloc(al*NTRANS, sizeof(float));
	ostack=calloc(NTRANS*GRID*GRID, sizeof(float));
	temp=calloc(NTRANS*GRID*GRID, sizeof(float));
	transform(in, stacks, 1);
	transform(out, ostack, -1);
	for (atlayer=0;atlayer<LAYERS;atlayer++)
	{
		for (iter=0;iter<NTRANS;iter++)
		{
			*(weights+atlayer*NTRANS+iter)=1.0;
		}
	}
	for (iter=0;iter<par->maxiter;iter++)
	{
		printf("%i\n", iter);

		addstack(stacks, weights, forward); 
		//printf("%.2f\n", fasum(forward, GRID*GRID));

		for (atlayer=1;atlayer<LAYERS;atlayer++)
		{
			transform(forward+(atlayer-1)*GRID*GRID, stacks+atlayer*NTRANS*GRID*GRID, 1);		
			addstack(stacks+atlayer*NTRANS*GRID*GRID, weights+atlayer*NTRANS, forward+atlayer*GRID*GRID);
		}

		addstack(ostack, weights+(LAYERS-1)*NTRANS, reverse+(LAYERS-1)*GRID*GRID);		
		for (atlayer=LAYERS-2;atlayer>=0;atlayer--)
		{
			transform(reverse+(atlayer+1)*GRID*GRID, temp, -1);	
			
			//test=fasum(temp, NTRANS*GRID*GRID);
			//if (test!=test) {exit(1);}
			addstack(temp, weights+atlayer*NTRANS, reverse+atlayer*GRID*GRID); 
			
		}

		done=1;
		for (atlayer=0;atlayer<LAYERS;atlayer++)
		{
			if (atlayer==LAYERS-1)
				checkmatch(stacks+atlayer*NTRANS*GRID*GRID, out, q);
			else
				checkmatch(stacks+atlayer*NTRANS*GRID*GRID, reverse+(atlayer+1)*GRID*GRID, q);
			//printf("al -- %i -- \n", atlayer);
			
			if (adjweights(q, weights+atlayer*NTRANS, par->kappa))
				done=0;
		}
		
		if (done)
			break;
	}
	printf("Convergence Reached\n");
	for (atlayer=0;atlayer<LAYERS;atlayer++)
	{
		printf("%i -> \n", atlayer);
		for (iter=0;iter<NTRANS; iter++)
		{
			if (*(weights+atlayer*NTRANS+iter)!=0)
				printf("%i ", iter);
		}
		printf("\n");
	}	
}



main()
{
	struct mscpars par;
	mktransmat();
	par.maxiter=80;
	par.kappa=.5;
	float inp[GRID][GRID];
	float outp[GRID][GRID];
	int i, j;
	for (i=0;i<GRID;i++)
	{
		for (j=0;j<GRID;j++)
		{
			inp[i][j]=0.0;
			outp[i][j]=0.0;
		}
	}	
	inp[39][39]=1.0;
	//outp[69][39]=1.0;
	outp[69][39]=1.0;
	printf("Starting\n");
	printf("par.maxiter=%i, par.kappa=%.3f\n", par.maxiter, par.kappa);
	mapseek(inp, outp, &par);
	printf("Done\n");
}
