fn main() {
	let x = 5;
	let x = x +  1;
	//println!("The value of x is:  {x}");
	//x = 6;
	
	{
		let x = x*2;
		println!("The alue of x in inner scope is: {x}");
	}

	println!("The value of x is: {x}");
	
}
