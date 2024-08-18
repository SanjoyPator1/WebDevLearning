import prisma from '../db'
import { comparePassword, createJWT, hashPassword } from '../modules/auth'

export const createNewUser = async (req,res,next)=>{
    try{
        const user = await prisma.user.create({
            data: {
                username: req.body.username,
                password: await hashPassword(req.body.password)
            }
        })
    
        const token = createJWT(user)
        //same as res.json({token : token})
        res.json({token})
    }catch(e){
        e.type = 'input'
        next(e)
    }
}

export const signin = async (req,res) =>{

    console.log("signin ",req.body)

    const user = await prisma.user.findUnique({
        where: {
            username : req.body.username,
        }
    })

    const isValid = await comparePassword(req.body.password, user.password)

    if(!isValid){
        res.status(401)
        res.json({
            message: "incorrect password"
        })
    }

    //create token
    const token = createJWT(user)
    //same as res.json({token : token})
    res.json({token})
    
}
