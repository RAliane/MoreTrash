mod decorator;
use crate::decorator::decorator;

//#[decorate]
fn main() {
        let sum = 5 + 10;
        let difference = 95.5 - 4.3; // Fixed typo: differnce -> difference
        let product = 4 * 30;
        let quotient = 56.7 / 32.2;
        let truncated = -5 / 3;
        let modulo = 43 % 5;
        let t = true;
        let f: bool = false;
	let c = 'z';
	let z: char = 'ℤ';
	let heart_eyed_cat ='😻';
	let x: (i32, f64, u8) =(500,6.4,1);
        
	decorator();
        println!("sum:\t\t{sum}");
        println!("difference:\t{difference}");
        println!("product:\t{product}");
        println!("quotient:\t{quotient}");
        println!("truncated:\t{truncated}");
        println!("modulo:\t\t{modulo}");
        println!("true:\t\t{t}\nfalse:\t\t{f}");
        decorator();
	println!("\t\t{c}\n\t\t{z}\n\t\t{heart_eyed_cat}");
	decorator();
	println!("\t\t{0}\n\t\t{1}\n\t\t{2}",x.0,x.1,x.2);
	decorator();
}
