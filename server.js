const express = require("express");

const app = express();

app.use(express.json());
app.use(express.static("public"));

let users = {};

function persianToEnglish(str){

return String(str).replace(/[۰-۹]/g, d =>
"۰۱۲۳۴۵۶۷۸۹".indexOf(d)
);

}


function getUser(id){

if(!users[id]){

users[id]={
balance:10000
};

}

return users[id];

}



// تست سرور
app.get("/",(req,res)=>{

res.send("🚀 DOGS LIMBO SERVER ONLINE");

});




// گرفتن موجودی

app.get("/balance/:id",(req,res)=>{


let user=getUser(req.params.id);


res.json({

balance:user.balance

});


});






// بازی LIMBO

app.post("/limbo",(req,res)=>{


let id=req.body.id;


let bet=Number(
persianToEnglish(req.body.bet)
);


let target=Number(
persianToEnglish(req.body.target)
);



let user=getUser(id);



if(!bet || !target){

return res.json({

error:"مقدار اشتباه"

});

}



if(bet > user.balance){

return res.json({

error:"موجودی کافی نیست"

});

}



user.balance -= bet;



let crash = Number(
(Math.random()*5+1).toFixed(2)
);



if(target <= crash){


let win = Math.floor(
bet * target
);


user.balance += win;



return res.json({

win:true,

prize:win,

crash:crash,

balance:user.balance

});


}



res.json({

win:false,

crash:crash,

balance:user.balance

});

});







// شارژ

app.post("/charge",(req,res)=>{


let id=req.body.id;

let amount=Number(
persianToEnglish(req.body.amount)
);



let user=getUser(id);


user.balance += amount;



res.json({

balance:user.balance

});


});







app.listen(3000,()=>{

console.log(
"🚀 SERVER RUNNING ON 3000"
);

});
