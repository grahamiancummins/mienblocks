import std.math;

int round(float n)
{
	if (n>=0)
		return cast(int) (n+.5);
	else
		return cast(int) (n-.5);
}

class Transform
{
	int[2][] transmat;
	this(int nt, float len)
	{
		double res=std.math.PI*2/nt;
		double theta, x, y;
		this.transmat.length=nt;
		for (int i=0;i<nt;i++)
		{
			theta=res*i;
			this.transmat[i][0]=round(cos(theta)*len);
			this.transmat[i][1]=round(sin(theta)*len);
			//printf("%i %.2f %i %i\n", i, theta, this.transmat[i][0], this.transmat[i][1]);
		}
		//printf("%i %i\n", this.transmat.length, this.transmat[0].length);
	}
	
	public int[] get(int i)
	{
		return this.transmat[i][0..2];
	}
	
	public void apply(float[][] inp, int scale, float outp[][][])
	{
		for (int i=0;i<this.transmat.length;i++)
		{
			outp[i]=this.shift(this.transmat[i][0], this.transmat[i][1], inp);
		}
	}
	
	private float[][] shift(int x, int y, float[][] inp)
	{
		if (x==0 && y==0) {return inp;}
		float[][] outp;
		outp.length=inp.length;
		for (int i=0;i<inp.length;i++)
		{
			outp[i].length=inp[i].length;
			outp[i][]=0.0;
		}
		//outp=inp.dup();
		for (int i=0;i<inp.length;i++)
		{
			for (int j=0;j<inp[0].length;j++)
			{
				if (i-x>=0 && i-x<inp.length && j-y>=0 && j-y<inp[0].length)
				{
					outp[i][j]=inp[i-x][j-y];
				} 
			}
		}
		return outp;
		
	}
	
	public int length()
	{
		return this.transmat.length;
	}
}

struct mscpar 
{
	int maxiter;
	float kappa;
	int layers;
	Transform trans;
}

float asum(float[] a)
{
	float sum=0.0;
	for (int i=0;i<a.length;i++)
		sum+=a[i];
	return sum;
}

float asum2(float[][] a)
{
	float sum=0.0;
	for (int i=0;i<a.length;i++)
		for (int j=0;j<a[0].length;j++)
			sum+=a[i][j];
	return sum;
}

float asum3(float[][][] a)
{
	float sum=0.0;
	for (int i=0;i<a.length;i++)
		for (int j=0;j<a[0].length;j++)
			for (int k=0;k<a[0][0].length;k++)
				sum+=a[i][j][k];
	return sum;
}

class Mapseeker
{
	mscpar pars;
	float[][] weights;
	float[][][] fimages;
	float[][][] rimages;
	float[][][][] stacks;
	float[][][] ostack;
	float[][][] temp;
	bool done;
	int iter;
	
	
	this (mscpar pars)
	{
		this.pars=pars;
		this.fimages.length=pars.layers;
		this.stacks.length=pars.layers;
		this.rimages.length=pars.layers;
		this.weights.length=pars.layers;
		int nt=pars.trans.length();
		for (int i=0; i<pars.layers; i++)
		{
			this.weights[i].length=nt;
			this.stacks[i].length=nt;
		}
		this.ostack.length=nt;
		this.temp.length=nt;
	}
	
	public void run(float[][] inp, float[][] outp)
	{
		this.done=false;
		this.iter=0;
		this.rimages[length-1]=outp;
		for (int i=0; i<pars.layers;i++)
			this.weights[i][]=1.0;
		this.pars.trans.apply(inp, 1, this.stacks[0]);
		this.pars.trans.apply(this.rimages[length-1], -1, ostack);
		while (!this.done && this.iter<this.pars.maxiter)
		{
			this.iterate();
		}
		printf("done\n");
		for (int i=0;i<this.pars.layers;i++)
		{	
			printf("%i ->\n", i);
			for (int j=0; j<this.weights[0].length;j++)
			{
				if (this.weights[i][j]!=0)
				{
					printf("%i\n", j);
				}
			}
		}
	}
	
	private float[][] addstack(float[][][] stack, float[] weights)
	{
		float[][] outp;
		float accum, max;
		int i,j,k;
		outp.length=stack[0].length;
		max=0;
		for (j=0;j<outp.length;j++)
		{
			outp[j].length=stack[0][j].length;
			outp[j][]=0;
		}	
		for (i=0; i<stack.length;i++)
		{
			for (j=0;j<outp.length;j++)
			{
				for (k=0;k<outp[0].length;k++)
				{
					outp[j][k]+=stack[i][j][k]*weights[i];
					if (outp[j][k]>max)
						max=outp[j][k];
				}
			}
		}
		for (j=0;j<outp.length;j++)
			for (k=0;k<outp[0].length;k++)
				outp[j][k]=outp[j][k]/max;
		
		return outp;
	}
	
	private float[] checkmatch(float[][][] stack, float[][] image)
	{
		float[] q;
		int i,j,k;
		float accum;
		float max=0.0;
		q.length=stack.length;
		//printf("%.2f %.2f\n", asum3(stack), asum2(image));
		for(i=0;i<q.length;i++)
		{
			accum=0.0;
			for(j=0;j<image.length;j++)
			{
				for (k=0;k<image[0].length;k++)
				{
					accum+=stack[i][j][k]*image[j][k];
				}
			}
			if (accum>max)
				max=accum;
			//else if (accum==0)	
			//	printf("%i %.2f\n", i, asum2(stack[i]));
			q[i]=accum;
		}
		if (max==0)
		{
			throw new Exception("No match");
		}
		for (i=0;i<q.length;i++)
			q[i]=q[i]/max;
		return q;
	}
	
	private bool adjweights(float[] q, float[] w)
	{
		int l;
		float max, pen, nw;
		bool done;
		done=true;
		max=0.0;
		for (l=0;l<q.length;l++)
		{
			pen=this.pars.kappa*(1-q[l]);
			nw=w[l]-pen;
			if (nw<0)
				nw=0.0;
			else if (nw>max)
				max=nw;
			//printf("%.2f %.2f %.2f\n", q[l], w[l], nw);
			w[l]=nw;
		}
		for (l=0;l<w.length;l++)
		{	
			w[l]=w[l]/max;
			if (w[l]>.05 && w[l]<.95)
				done=false;
		}	
		return done;
	}
	
	private void iterate()
	{
		int i,nl;
		bool check;
		float[] q;
		q.length=pars.trans.length();
		nl=this.pars.layers;
		printf("%i\n", this.iter);
		//printf("%.2f\n", asum3(this.stacks[0]));
		this.fimages[0]=this.addstack(this.stacks[0], this.weights[0]);
		for (i=1;i<this.fimages.length;i++)
		{
			this.pars.trans.apply(this.fimages[i-1], 1, stacks[i]);
			this.fimages[i]=this.addstack(this.stacks[i], this.weights[i]);
		}
		this.rimages[nl-2]=this.addstack(this.ostack, this.weights[length-1]);
		for (i=nl-3;i>=0;i--)
		{
			this.pars.trans.apply(this.rimages[i+1], -1, this.temp);
			this.rimages[i]=this.addstack(temp, this.weights[i]);
		}
		this.done=true;
		for (i=0;i<nl;i++)
		{
			q=this.checkmatch(stacks[i], rimages[i]);
			check=this.adjweights(q, weights[i]);
			if (!check)
				this.done=false;
			/*for (int j=0;j<weights[i].length;j++)
			{
				printf("%.2f ", weights[i][j]);
			}
			printf("\n");*/
		}
		this.iter+=1;
	}
}

int main()
{
	Mapseeker findit;
	mscpar pars;
	float inp[][];
	float outp[][];
	
	inp.length=100;
	outp.length=100;
	for (int i=0;i<100; i++)
	{
		inp[i].length=100;
		inp[i][]=0.0;
		outp[i].length=100;
		outp[i][]=0.0;
	}
	inp[39][39]=1.0;
	outp[69][39]=1.0;
	pars.maxiter=200;
	pars.kappa=0.5;
	pars.layers=3;
	pars.trans=new Transform(72, 30.0);
	
	
	findit=new Mapseeker(pars);
	findit.run(inp, outp);
	//for (int r=0;r<pars.trans.transmat.length;r++)
	//	printf("%i %i\n", pars.trans.transmat[r][0], pars.trans.transmat[r][0]);
	
	return 0;
}

