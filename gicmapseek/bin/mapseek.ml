open Bigarray;;
(*ocamlopt -o mapml bigarray.cmxa mapseek.ml*)
type mscpar =
	{kappa:float;
	maxiter:int;
	grid:int;
	layers:int;
	ntrans:int;
	};;

let pars=
	{kappa=0.5;
	maxiter=80;
	grid=100;
	layers=3;
	ntrans=72;
	};;
(*
let ma1=fun d1->Array1.create Bigarray.float32 Bigarray.c_layout d1;;
	
let ma2=function
	(d1, d2)->Array2.create Bigarray.float32 Bigarray.c_layout d1 d2;;

let ma3=function
	(d1, d2, d3)->Array3.create Bigarray.float32 Bigarray.c_layout d1 d2 d3;;

let rec loadlist=function
	(_,_,0)->[]
	| (t, f, l)->f t :: loadlist (t,f,l-1);;

let forward=loadlist ((pars.grid, pars.grid), ma2,  3);;
(*let i=List.length(forward) in Printf.fprintf stdout "%i\n" i;;*)
let reverse=loadlist  ((pars.grid, pars.grid), ma2,  3);;
let weights=loadlist  (pars.ntrans, ma1,  3);;
let stacks=loadlist ((pars.ntrans, pars.grid, pars.grid), ma3, 3);;
let temp=ma3 pars.ntrans, pars.grid, pars.grid;;
*)

let forward=Array3.create Bigarray.float32 Bigarray.c_layout pars.layers pars.grid pars.grid;;
let reverse=Array3.create Bigarray.float32 Bigarray.c_layout pars.layers pars.grid pars.grid;;
let weight=Array2.create Bigarray.float32 Bigarray.c_layout pars.layers pars.ntrans;; 
let stack=Genarray.create Bigarray.float32 Bigarray.c_layout [|pars.layers; pars.ntrans; pars.grid;pars.grid|];;
let temp=Array3.create Bigarray.float32 Bigarray.c_layout pars.ntrans pars.grid pars.grid;;

Array2.fill weight 1.0;;

