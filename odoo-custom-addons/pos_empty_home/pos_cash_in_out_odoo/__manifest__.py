# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Pos Cash In Out - Odoo",
    "version" : "14.0.1.5",
    "category" : "Point of Sale",
    "depends" : ['base','sale','account','point_of_sale'],
    "author": "BrowseInfo",
    'summary': 'This app pos cash in out pos cash out pos cash operation pos cash out pos cash counter pos cash register cash control on pos cash in-out on pos cash in on pos cash out on pos cash in cash out on pos pos cash in cash out point of sale cash counter',
    "description": """
    
    Purpose :- 
This apps helps seller to perform Cash In, Cash Out Operation from POS. 
    pos cash in out
    pos cash out
    pos cash operation
    pos cash control
	pos cash counter
	pos cash register
    cash control on pos
    cash in-out on pos
    cash in on pos
    cash out on pos
    cash in cash out on pos
    pos cash in cash out
    
    point of sale cash in out
    point of sale cash out
    point of sale cash operation
    point of sale cash control
    cash control on point of sale
    cash in-out on point of sale
    cash in on point of sale
    cash out on point of sale
    cash in cash out on point of sale
    point of sale cash in cash out

    point of sales cash in out
    point of sales cash out
    point of sales cash operation
    point of sales cash control
    cash control on point of sales
    cash in-out on point of sales
    cash in on point of sales
    cash out on point of sales
    cash in cash out on point of sales
    point of sales cash in cash out

pos cash out pos cash opération de trésorerie pos contrôle de trésorerie pos contrôle de la trésorerie sur pos encaissement sur pos encaisser sur pos encaisser sur pos espèces en espèces sur pos pos cash en espèces point de vente comptant point de vente opération de caisse au point de vente contrôle de caisse au point de vente contrôle de trésorerie sur le point de vente encaissement sur le point de vente encaisser sur le point de vente encaisser sur le point de vente encaissement sur le point de vente point de vente comptant en espèces point de vente encaissement point de vente encaissement opération d'encaissement au point de vente contrôle des espèces au point de vente contrôle de trésorerie sur le point de vente encaissement sur le point de vente encaisser sur le point de vente encaisser sur le point de vente encaissement sur le point de vente point de vente comptant en espèces

وضع النقدية في الخارج
     دفع النقود
     عملية النقدية pos
     مراقبة النقدية
     مراقبة النقدية على نقاط البيع
     النقد في الخروج على نقاط البيع
     نقدا في نقاط البيع
     النقد على pos
     النقد نقدا على pos
     نقدي النقدية نقدا
    
     نقطة البيع نقدا في الخارج
     نقطة بيع النقد خارج
     نقطة البيع النقدية
     نقطة البيع السيطرة النقدية
     السيطرة النقدية على نقطة البيع
     نقدا في نقطة البيع
     النقد في نقطة البيع
     نقدا على نقطة البيع
     نقدا نقدا في نقطة البيع
     نقطة البيع نقدا نقدا

     نقطة البيع نقدا في الخارج
     نقطة البيع نقدا
     نقطة البيع النقدية
     نقطة السيطرة على المبيعات النقدية
     السيطرة النقدية على نقطة البيع
     نقدا في نقطة البيع
     النقدية في نقطة البيع
     النقد خارج على نقطة البيع
     نقدا نقدا في نقطة البيع
   postar dinheiro fora
     receber dinheiro
     operação pós-caixa
     pos controle de caixa
     controle de caixa em pos
     entrada de dinheiro na pos
     dinheiro em pos
     dinheiro para fora em pos
     dinheiro em dinheiro na pos
     pagar dinheiro em dinheiro
    
     ponto de venda em dinheiro
     saída do ponto de venda
     Operação em dinheiro do ponto de venda
     controle de caixa do ponto de venda
     controle de caixa no ponto de venda
     entrada de dinheiro no ponto de venda
     dinheiro no ponto de venda
     dinheiro no ponto de venda
     dinheiro em dinheiro no ponto de venda
     ponto de venda dinheiro em dinheiro

     ponto de venda em dinheiro
     saída do ponto de venda
     operação de caixa de ponto de venda
     controle de caixa do ponto de venda
     Controle de caixa no ponto de venda
     entrada em dinheiro no ponto de venda
     dinheiro no ponto de venda
     dinheiro no ponto de venda
     dinheiro em dinheiro no ponto de vendas
     ponto de venda em dinheiro na saída de caixa

pos efectivo en fuera
     salida de efectivo
     Operación pos cash
     control de efectivo pos
     control de efectivo en pos
     entrada y salida de efectivo en pos
     ingreso en efectivo en pos
     retirar efectivo en pos
     efectivo en efectivo en pos
     pos efectivo en efectivo
    
     punto de venta efectivo fuera
     punto de venta retiro
     operación de efectivo en el punto de venta
     control de efectivo en el punto de venta
     control de efectivo en el punto de venta
     entrada de efectivo en el punto de venta
     cobrar en el punto de venta
     retirar efectivo en el punto de venta
     efectivo en efectivo en el punto de venta
     punto de venta efectivo en efectivo

     punto de venta efectivo en efectivo
     punto de venta retiro
     operación de efectivo en el punto de venta
     control de efectivo en el punto de venta
     control de efectivo en el punto de venta
     entrada y salida de efectivo en el punto de venta
     cobrar en el punto de venta
     retirar efectivo en el punto de venta
     cobrar efectivo en el punto de venta
     punto de venta efectivo en efectivo
    
    """,
    "website" : "https://www.browseinfo.in",

    "price": 15,

    "currency": "EUR",

    "data": [
        'security/ir.model.access.csv',
        'views/custom_pos_view.xml',
    ],

    'qweb': [
        'static/src/xml/pos.xml',
    ],
    "auto_install": False,
    "installable": True,
    "live_test_url":"https://youtu.be/Juuhr2V95-A",
    "images":['static/description/Banner.png'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
