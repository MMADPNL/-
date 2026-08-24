const express = require("express");

const app = express();

app.use(express.json());
app.use(express.static("public"));

let users = {};

function getUser(id){
    if(!users[id]){
        users[id] = {
            balance: 10000
        };
    }

    return users[id];
}


app.get("/", (req,res)=>{
    res.send("🚀 DOGS LIMBO SERVER ONLINE");
});


// موجودی
app.get("/balance/:id",(req,res)=>{

    let user = getUser(req.params.id);

    res.json({
        balance: user.balance
    });

});


// بازی LIMBO
app.post("/limbo",(req,res)=>{

    let id = req.body.id;
    let bet = Number(req.body.bet);
    let target = Number(req.body.target);

    let user = getUser(id);


    if(!bet || !target){

        return res.json({
            error:"عدد اشتباه"
        });

    }


    if(bet > user.balance){

        return res.json({
            error:"موجودی کافی نیست"
        });

    }


    user.balance -= bet;


    let crash = Number(
        (Math.random()*9+1).toFixed(2)
    );


    if(target <= crash){

        let win = Math.floor(
            bet * target
        );

        user.balance += win;


        return res.json({

            win:true,

            prize:win,

            balance:user.balance

        });

    }


    res.json({

        win:false,

        crash:crash,

        balance:user.balance

    });


});


// شارژ تستی
app.post("/charge",(req,res)=>{

    let user = getUser(req.body.id);

    user.balance += Number(
        req.body.amount
    );


    res.json({

        balance:user.balance

    });

});



app.listen(3000,()=>{

    console.log(
        "🚀 SERVER RUNNING"
    );

});
