
type dataset = {fs:float; data:float array array;};;


let rec print_list = function
	[] -> ()
	| a :: b -> print_int a;print_newline (); print_list b;;

let input_int32 ic bo =
	let l= ref [] in
	for i=1 to 4 do
		let by=input_byte ic in
		l := by :: !l
	done;	
	if bo = 'l' then
		l := List.rev !l;
	let a = Array.of_list !l in
	let base = Int32.of_int (a.(0) lor (a.(1) lsl 8) lor (a.(2) lsl 16)) in
	let big = Int32.shift_left (Int32.of_int a.(3)) 24 in
	Int32.logor base big;;

let input_float ic bo =
	let i = input_int32 ic bo in
	Int32.float_of_bits i;;
	
let input_float_matrix ic bo nrow ncol =
	let m=Array.make_matrix nrow ncol 0.0 in
	for i=0 to nrow-1 do
		for j=0 to ncol-1 do
			m.(i).(j) <- input_float ic bo;
		done;
	done;	
	m;;

(* all output functions should be little endian *) 

let output_int32 ch n =
	let base = Int32.to_int n in
	let big = Int32.to_int (Int32.shift_right_logical n 24) in
	output_byte ch base;
	output_byte ch (base lsr 8);
	output_byte ch (base lsr 16);
	output_byte ch big;;

let output_float ch f =
	output_int32 ch (Int32.bits_of_float f);;

let output_float_matrix ch a =
	for i=0 to (Array.length a)-1 do
		let sa=a.(i) in
		for j=0 to (Array.length sa) -1 do
			output_float ch a.(i).(j)
		done;
	done;;	

let read_saf fname =
	let ic = open_in_bin fname in
	let icl = in_channel_length ic in 
	let ibuf= String.create 5 in
	let nr= input ic ibuf 0 5 in
	if ibuf <> "SAF01" then failwith "This is not an SAF file" ;
	let bo = input_char ic in
	let ncol = Int32.to_int (input_int32 ic bo) in
	let nrow = (icl-14)/(4*ncol) in
	let fs=input_float ic bo in
	let q =  {fs=fs; data=input_float_matrix ic bo nrow ncol} in 
	close_in ic;
	q;;

let write_saf fname ds =
	let ncol=Array.length ds.data.(0) in
	let oc = open_out_bin fname in 
	output_string oc "SAF01l";
	output_int32 oc (Int32.of_int ncol);
	output_float oc ds.fs;
	output_float_matrix oc ds.data;
	close_out oc;;
		
	

let q=Sys.argv.(1) ;;
print_endline q;;
let z=read_saf q ;; 
Printf.fprintf stdout "%.3f\n" z.data.(2).(0);;
Printf.fprintf stdout "%.3f\n" z.fs;;
write_saf Sys.argv.(2) z;;

